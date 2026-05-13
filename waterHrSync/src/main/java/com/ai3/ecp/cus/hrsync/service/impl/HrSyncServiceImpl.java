package com.ai3.ecp.cus.hrsync.service.impl;

import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.jeedsoft.common.advanced.db.dataset.DataSet;
import com.jeedsoft.common.advanced.db.dataset.Record;
import com.jeedsoft.quicksilver.base.service.impl.EntityServiceImpl;
import com.jeedsoft.quicksilver.base.type.ServiceContext;

import com.ai3.ecp.cus.hrsync.HrSyncHome;
import com.ai3.ecp.cus.hrsync.model.HrSyncModel;
import com.ai3.ecp.cus.hrsync.service.HrSyncService;

public class HrSyncServiceImpl extends EntityServiceImpl<HrSyncModel> implements HrSyncService
{
	private static final Logger logger = LoggerFactory.getLogger(HrSyncServiceImpl.class);

	public HrSyncServiceImpl()
	{
		super(HrSyncHome.UNIT_ID, HrSyncModel.class);
	}

	@Override
	public void syncHrData(ServiceContext sc)
	{
		logger.info("[syncHrData] Start");
		Date startTime = new Date();
		int totalCount = 0, successCount = 0, failCount = 0;

		// Step 1: Get HR user list (all users from v_KM_USER)
		DataSet<Record> hrUserList;
		try {
			hrUserList = HrSyncHome.getDao().getHrUserList();
		} catch (Exception e) {
			logger.error("[syncHrData] 執行時間: {}, 功能名稱: syncHrData, 錯誤訊息: 無法取得人事資料 — {}", startTime, e.getMessage(), e);
			return;
		}
		logger.debug("[syncHrData] HR user list size: {}", hrUserList.size());

		// Step 2: Sync department hierarchy from v_KM_DEPT → TsDepartment
		// Returns map: HR DEPARTMENTID → ECP TsDepartment.FId
		Map<String, UUID> hrDeptIdToEcpFId;
		try {
			hrDeptIdToEcpFId = syncDepartments();
		} catch (Exception e) {
			logger.error("[syncHrData] 執行時間: {}, 功能名稱: syncHrData, 錯誤訊息: 無法同步部門資料 — {}", startTime, e.getMessage(), e);
			return;
		}

		// Step 3: Build HR lookup map by AD login ID (TsUser.FLoginName)
		Map<String, Record> hrUserByLogin = new HashMap<>();
		for (Record hrUser : hrUserList) {
			String loginId = hrUser.getString("LOGINID");
			if (loginId == null || loginId.trim().isEmpty()) {
				continue;
			}
			String rawLogin = loginId.trim().toLowerCase();
			hrUserByLogin.put(rawLogin, hrUser);
		}

		// Step 4: Load existing ECP users. They are manually created by water team.
		DataSet<Record> ecpUsers = HrSyncHome.getDao().getAllEcpUsers();

		// Step 5: Collect IT department IDs for role assignment check
		Set<String> itDeptIds = new HashSet<>();
		try {
			DataSet<Record> itDepts = HrSyncHome.getDao().getItDeptList();
			for (Record dept : itDepts) {
				String id = dept.getString("DEPARTMENTID");
				if (id != null) {
					itDeptIds.add(id.trim());
				}
			}
		} catch (Exception e) {
			logger.warn("[syncHrData] 無法取得資訊處部門清單，IT 角色指派將略過: {}", e.getMessage());
		}

		// Step 6: Load roles (non-fatal — sync continues without role assignment if unavailable)
		DataSet<Record> defaultRoles = null;
		try {
			defaultRoles = HrSyncHome.getDao().getDefaultRoles();
		} catch (Exception e) {
			logger.warn("[syncHrData] 無法取得角色資料，角色指派將略過: {}", e.getMessage());
		}

		// Step 7: Update existing TsUser/TsAccount by AD login (manual account onboarding)
		totalCount = ecpUsers.size();
		for (Record ecpUser : ecpUsers) {
			UUID userId = ecpUser.getUuid("FId");
			Record account = HrSyncHome.getDao().getAccountByUserId(userId);
			if (account == null) {
				logger.debug("[syncHrData] Skip TsUser without mapped TsAccount, userId={}", userId);
				continue;
			}

			String loginName = account.getString("FLoginName");
			if (loginName == null || loginName.trim().isEmpty()) {
				logger.debug("[syncHrData] Skip TsAccount without login name, userId={}, accountId={}", userId, account.getUuid("FId"));
				continue;
			}

			String loginKey = loginName.trim().toLowerCase();
			Record hrUser = hrUserByLogin.get(loginKey);
			if (hrUser == null) {
				logger.debug("[syncHrData] Login {} has no 00-department HR data, skip update", loginName);
				continue;
			}

			String employeeId = hrUser.getString("EMPLOYEEID");
			if (employeeId != null) {
				employeeId = employeeId.trim();
			}
			String displayName = hrUser.getString("DISPLAYNAME");
			String email = hrUser.getString("EMAILADDRESS");
			String hrDeptId = hrUser.getString("DEPARTMENTID");

			UUID userDeptFId = (hrDeptId != null) ? hrDeptIdToEcpFId.get(hrDeptId.trim()) : null;
			if (userDeptFId == null) {
				userDeptFId = HrSyncHome.DEPT_ROOT_FID;
				logger.warn("[syncHrData] AD {} 的部門 {} 無法對應，歸屬至根部門", loginName, hrDeptId);
			}

			try {
				HrSyncHome.getDao().updateEcpUser(userId, displayName, loginName.trim(), email, userDeptFId, employeeId);

				HrSyncHome.getDao().updateAccount(account.getUuid("FId"), displayName, loginName.trim(),
						HrSyncHome.DEFAULT_ACCOUNT_PASSWORD, email);
				ensureAccountIdentity(account.getUuid("FId"), displayName, userId);

				assignRoles(userId, defaultRoles);

				successCount++;
			} catch (Exception e) {
				logger.error("[syncHrData] 執行時間: {}, 功能名稱: syncHrData, 錯誤訊息: 同步 AD {} / 員工 {} 失敗 — {}",
						startTime, loginName, employeeId, e.getMessage(), e);
				failCount++;
			}
		}


		Date endTime = new Date();
		long processTime = (endTime.getTime() - startTime.getTime()) / 1000L;
		logger.info("[syncHrData] Finish, 執行時間: {}, 功能名稱: syncHrData, 總筆數: {}, 成功: {}, 失敗: {}, 處理時間: {}(s)",
				startTime, totalCount, successCount, failCount, processTime);
	}

	/**
	 * Syncs v_KM_DEPT into TsDepartment.
	 * Departments whose BELONGTO is null are parented to HrSyncHome.DEPT_ROOT_FID (集團).
	 * Departments whose BELONGTO points to another DEPARTMENTID are parented to
	 * that department's TsDepartment.FId.
	 *
	 * @return map of HR DEPARTMENTID → ECP TsDepartment.FId
	 */
	private Map<String, UUID> syncDepartments()
	{
		DataSet<Record> hrDepts = HrSyncHome.getDao().getHrDeptList();

		// Build HR dept map: DEPARTMENTID → record
		Map<String, Record> hrDeptMap = new HashMap<>();
		for (Record d : hrDepts) {
			String id = d.getString("DEPARTMENTID");
			if (id != null && !id.trim().isEmpty()) {
				hrDeptMap.put(id.trim(), d);
			}
		}

		// Build existing ECP dept lookup by name: FName → FId
		Map<String, UUID> ecpDeptByName = new HashMap<>();
		for (Record d : HrSyncHome.getDao().getAllEcpDepartments()) {
			String name = d.getString("FName");
			UUID fid = d.getUuid("FId");
			if (name != null && fid != null) {
				ecpDeptByName.put(name, fid);
			}
		}

		// Iterative topological processing: process parents before children
		Map<String, UUID> hrToEcpDeptId = new HashMap<>();
		Set<String> processed = new HashSet<>();
		int maxIterations = hrDeptMap.size() + 1;

		while (processed.size() < hrDeptMap.size() && maxIterations-- > 0) {
			for (Map.Entry<String, Record> entry : hrDeptMap.entrySet()) {
				String hrId = entry.getKey();
				if (processed.contains(hrId)) {
					continue;
				}
				Record d = entry.getValue();
				String belongTo = d.getString("BELONGTO");
				boolean belongToEmpty = belongTo == null || belongTo.trim().isEmpty();

				UUID parentEcpId;
				if (belongToEmpty) {
					parentEcpId = HrSyncHome.DEPT_ROOT_FID;
				} else if (hrToEcpDeptId.containsKey(belongTo.trim())) {
					parentEcpId = hrToEcpDeptId.get(belongTo.trim());
				} else if (!hrDeptMap.containsKey(belongTo.trim())) {
					parentEcpId = HrSyncHome.DEPT_ROOT_FID;
				} else {
					continue; // parent not yet processed — retry next iteration
				}

				String deptName = d.getString("DISPLAYNAME");
				UUID ecpDeptId = ecpDeptByName.get(deptName);
				if (ecpDeptId == null) {
					ecpDeptId = UUID.randomUUID();
					HrSyncHome.getDao().createDepartment(ecpDeptId, deptName, parentEcpId);
					ecpDeptByName.put(deptName, ecpDeptId);
					logger.debug("[syncDepartments] Created department '{}' id={}", deptName, ecpDeptId);
				} else {
					HrSyncHome.getDao().updateDepartment(ecpDeptId, deptName, parentEcpId);
					logger.debug("[syncDepartments] Updated department '{}' id={}", deptName, ecpDeptId);
				}
				hrToEcpDeptId.put(hrId, ecpDeptId);
				processed.add(hrId);
			}
		}

		if (processed.size() < hrDeptMap.size()) {
			logger.warn("[syncDepartments] {} 個部門因循環參照或父部門缺失而未能處理", hrDeptMap.size() - processed.size());
		}
		logger.debug("[syncDepartments] Synced {} departments", processed.size());
		return hrToEcpDeptId;
	}

	private void ensureAccountIdentity(UUID accountId, String name, UUID userId)
	{
		if (!HrSyncHome.getDao().hasAccountIdentity(accountId)) {
			UUID identityId = UUID.randomUUID();
			HrSyncHome.getDao().createAccountIdentity(identityId, name, accountId,
					HrSyncHome.DEFAULT_IDENTITY_TYPE_ID, userId);
			logger.info("已建立 TsAccountIdentity: account={} user={}", accountId, userId);
		}
	}

	private void assignRoles(UUID userId, DataSet<Record> defaultRoles)
	{
		if (defaultRoles != null) {
			for (Record role : defaultRoles) {
				UUID roleId = role.getUuid("FId");
				if (!HrSyncHome.getDao().hasRoleAssigned(roleId, userId)) {
					HrSyncHome.getDao().assignRoleToUser(roleId, userId);
				}
			}
		}
	}

}
