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

		// Step 3: Build lookup map of existing ECP users (keyed by FDID / employee ID)
		DataSet<Record> ecpUsers = HrSyncHome.getDao().getAllEcpUsers();
		Map<String, Record> ecpUserMap = new HashMap<>();
		for (Record user : ecpUsers) {
			String did = user.getString("FDID");
			if (did != null && !did.trim().isEmpty()) {
				ecpUserMap.put(did.trim(), user);
			}
		}

		// Step 4: Collect IT department IDs for role assignment check
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

		// Step 5: Load roles (non-fatal — sync continues without role assignment if unavailable)
		DataSet<Record> defaultRoles = null;
		DataSet<Record> sysAdminRoles = null;
		try {
			defaultRoles = HrSyncHome.getDao().getDefaultRoles();
			sysAdminRoles = HrSyncHome.getDao().getSysAdminRoles();
		} catch (Exception e) {
			logger.warn("[syncHrData] 無法取得角色資料，角色指派將略過: {}", e.getMessage());
		}

		// Step 6: Process each HR user — create or update ECP user + account + roles
		Set<String> hrEmployeeIds = new HashSet<>();
		totalCount = hrUserList.size();

		for (Record hrUser : hrUserList) {
			String employeeId = hrUser.getString("EMPLOYEEID");
			if (employeeId == null || employeeId.trim().isEmpty()) {
				continue;
			}
			employeeId = employeeId.trim();
			hrEmployeeIds.add(employeeId);

			String displayName = hrUser.getString("DISPLAYNAME");
			String email = hrUser.getString("EMAILADDRESS");
			String loginId = hrUser.getString("LOGINID");
			String hrDeptId = hrUser.getString("DEPARTMENTID");

			// Resolve user's ECP department FId; fall back to root if not mapped
			UUID userDeptFId = (hrDeptId != null) ? hrDeptIdToEcpFId.get(hrDeptId.trim()) : null;
			if (userDeptFId == null) {
				userDeptFId = HrSyncHome.DEPT_ROOT_FID;
				logger.warn("[syncHrData] 員工 {} 的部門 {} 無法對應，歸屬至根部門", employeeId, hrDeptId);
			}

			try {
				UUID userId;
				Record ecpUser = ecpUserMap.get(employeeId);

				if (ecpUser == null) {
					// 名單存在，ECP 不存在 → 新增
					userId = UUID.randomUUID();
					HrSyncHome.getDao().createEcpUser(userId, displayName, loginId, email, userDeptFId, employeeId);
					logger.debug("[syncHrData] Created user employeeId={}", employeeId);

					UUID accountId = UUID.randomUUID();
					HrSyncHome.getDao().createAccount(accountId, displayName, loginId, HrSyncHome.DEFAULT_ACCOUNT_PASSWORD, email);
					ensureAccountIdentity(accountId, displayName, userId);
				} else {
					// 名單存在，ECP 存在 → 更新
					userId = ecpUser.getUuid("FId");
					HrSyncHome.getDao().updateEcpUser(userId, displayName, loginId, email, userDeptFId);
					logger.debug("[syncHrData] Updated user employeeId={}", employeeId);

					Record account = (loginId != null) ? HrSyncHome.getDao().getAccountByLoginName(loginId) : null;
					if (account == null) {
						UUID accountId = UUID.randomUUID();
						HrSyncHome.getDao().createAccount(accountId, displayName, loginId, HrSyncHome.DEFAULT_ACCOUNT_PASSWORD, email);
						ensureAccountIdentity(accountId, displayName, userId);
					} else {
						HrSyncHome.getDao().updateAccount(account.getUuid("FId"), displayName, loginId, email);
						ensureAccountIdentity(account.getUuid("FId"), displayName, userId);
					}
				}

				// Role assignment: default role always; sysAdmin role for IT personnel
				boolean isItPerson = hrDeptId != null && itDeptIds.contains(hrDeptId.trim());
				assignRoles(userId, defaultRoles, sysAdminRoles, isItPerson);

				successCount++;
			} catch (Exception e) {
				logger.error("[syncHrData] 執行時間: {}, 功能名稱: syncHrData, 錯誤訊息: 處理人員 {} 失敗 — {}", startTime, employeeId, e.getMessage(), e);
				failCount++;
			}
		}

		// Step 7: Disable ECP users absent from HR list — skip customer service staff (FIsServices=1)
		for (Map.Entry<String, Record> entry : ecpUserMap.entrySet()) {
			String empId = entry.getKey();
			if (!hrEmployeeIds.contains(empId)) {
				Record ecpUser = entry.getValue();
				String isServicesVal = ecpUser.getString("FIsServices");
				boolean isServices = "1".equals(isServicesVal) || "true".equalsIgnoreCase(isServicesVal);
				if (isServices) {
					logger.debug("[syncHrData] Skipped disable for customer service staff employeeId={}", empId);
					continue;
				}
				try {
					UUID userId = ecpUser.getUuid("FId");
					HrSyncHome.getDao().disableEcpUser(userId);

					String loginName = ecpUser.getString("FLoginName");
					if (loginName != null && !loginName.trim().isEmpty()) {
						Record account = HrSyncHome.getDao().getAccountByLoginName(loginName);
						if (account != null) {
							HrSyncHome.getDao().disableAccount(account.getUuid("FId"));
						}
					}
					logger.debug("[syncHrData] Disabled user not in HR list, employeeId={}", empId);
				} catch (Exception e) {
					logger.error("[syncHrData] 執行時間: {}, 功能名稱: syncHrData, 錯誤訊息: 停用人員 {} 失敗 — {}", startTime, empId, e.getMessage(), e);
				}
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

	private void assignRoles(UUID userId, DataSet<Record> defaultRoles, DataSet<Record> sysAdminRoles, boolean isItPerson)
	{
		if (defaultRoles != null) {
			for (Record role : defaultRoles) {
				UUID roleId = role.getUuid("FId");
				if (!HrSyncHome.getDao().hasRoleAssigned(roleId, userId)) {
					HrSyncHome.getDao().assignRoleToUser(roleId, userId);
				}
			}
		}
		if (isItPerson && sysAdminRoles != null) {
			for (Record role : sysAdminRoles) {
				UUID roleId = role.getUuid("FId");
				if (!HrSyncHome.getDao().hasRoleAssigned(roleId, userId)) {
					HrSyncHome.getDao().assignRoleToUser(roleId, userId);
				}
			}
		}
	}
}
