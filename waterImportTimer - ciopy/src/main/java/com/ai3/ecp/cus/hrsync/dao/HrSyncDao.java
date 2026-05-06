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
	DataSet<Record> getItDeptList();

	// TsDepartment
	DataSet<Record> getDepartmentByName(String name);
	void createDepartment(UUID id, String name);

	// TsUser
	DataSet<Record> getEcpUsersByDeptId(UUID deptId);
	Record getEcpUserByEmployeeId(String employeeId);
	void createEcpUser(UUID id, String name, String loginName, String email, UUID deptId, String employeeId);
	void updateEcpUser(UUID id, String name, String loginName, String email);
	void disableEcpUser(UUID id);

	// TsAccount
	Record getAccountByLoginName(String loginName);
	void createAccount(UUID id, String name, String loginName, String email);
	void updateAccount(UUID id, String name, String loginName, String email);
	void disableAccount(UUID id);

	// TsRole / TsRoleUser
	DataSet<Record> getDefaultRoles();
	DataSet<Record> getSysAdminRoles();
	boolean hasRoleAssigned(UUID roleId, UUID userId);
	void assignRoleToUser(UUID roleId, UUID userId);
}