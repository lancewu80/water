package com.ai3.ecp.cus.hrsync.dao;

import java.util.UUID;

import com.jeedsoft.common.advanced.db.dataset.DataSet;
import com.jeedsoft.common.advanced.db.dataset.Record;
import com.jeedsoft.quicksilver.base.dao.EntityDao;

import com.ai3.ecp.cus.hrsync.model.HrSyncModel;

public interface HrSyncDao extends EntityDao<HrSyncModel>
{
	// HR source views (v_KM_USER, v_KM_DEPT)
	DataSet<Record> getHrUserList();
	DataSet<Record> getHrDeptList();
	DataSet<Record> getItDeptList();

	// TsDepartment
	DataSet<Record> getAllEcpDepartments();
	DataSet<Record> getDepartmentByName(String name);
	void createDepartment(UUID id, String name, UUID parentId);
	void updateDepartment(UUID id, String name, UUID parentId);

	// TsUser
	DataSet<Record> getAllEcpUsers();
	DataSet<Record> getEcpUsersByDeptId(UUID deptId);
	Record getEcpUserByEmployeeId(String employeeId);
	void createEcpUser(UUID id, String name, String loginName, String email, UUID deptId, String employeeId);
	void updateEcpUser(UUID id, String name, String loginName, String email, UUID deptId, String employeeId);
	void disableEcpUser(UUID id);

	// TsAccount
	Record getAccountByLoginName(String loginName);
	Record getAccountByUserId(UUID userId);
	void createAccount(UUID id, String name, String loginName, String password, String email);
	void updateAccount(UUID id, String name, String loginName, String password, String email);
	void disableAccount(UUID id);

	// TsAccountIdentity
	boolean hasAccountIdentity(UUID accountId);
	void createAccountIdentity(UUID id, String name, UUID accountId, UUID identityTypeId, UUID entityId);

	// TsRole / TsRoleUser
	DataSet<Record> getDefaultRoles();
	DataSet<Record> getSysAdminRoles();
	boolean hasRoleAssigned(UUID roleId, UUID userId);
	void assignRoleToUser(UUID roleId, UUID userId);
}
