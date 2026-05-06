package com.ai3.ecp.cus.hrsync.dao.impl;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import com.jeedsoft.common.advanced.db.dataset.DataSet;
import com.jeedsoft.common.advanced.db.dataset.Record;
import com.jeedsoft.quicksilver.base.dao.impl.EntityDaoImpl;

import com.ai3.ecp.cus.hrsync.HrSyncHome;
import com.ai3.ecp.cus.hrsync.dao.HrSyncDao;
import com.ai3.ecp.cus.hrsync.model.HrSyncModel;

public class HrSyncDaoImpl extends EntityDaoImpl<HrSyncModel> implements HrSyncDao
{
	public HrSyncDaoImpl()
	{
		super(HrSyncHome.UNIT_ID, HrSyncModel.class);
	}

	// ── HR source ──────────────────────────────────────────────────────────────

	@Override
	public DataSet<Record> getHrUserList()
	{
		return getExecutor("km").getDataSet(
				"SELECT EMPLOYEEID, DISPLAYNAME, EMAILADDRESS, LOGINID, DEPARTMENTID " +
						"FROM v_KM_USER " +
						"WHERE DEPARTMENTID LIKE '00%' " +
						"AND EMPLOYEEID IS NOT NULL " +
						"AND LTRIM(RTRIM(EMPLOYEEID)) <> ''",
				new Object[]{});
	}

	@Override
	public DataSet<Record> getHrDeptList()
	{
		return getExecutor("km").getDataSet(
				"SELECT DEPARTMENTID, DISPLAYNAME, BELONGTO FROM v_KM_DEPT WHERE DEPARTMENTID LIKE '00%'",
				new Object[]{});
	}

	@Override
	public DataSet<Record> getItDeptList()
	{
		return getExecutor("km").getDataSet(
				"SELECT DEPARTMENTID FROM v_KM_DEPT WHERE DEPARTMENTID LIKE '00%' AND DISPLAYNAME LIKE N'%資訊%'",
				new Object[]{});
	}

	// ── TsDepartment ───────────────────────────────────────────────────────────

	@Override
	public DataSet<Record> getAllEcpDepartments()
	{
		return getExecutor("default").getDataSet(
				"SELECT FId, FName, FParentId FROM TsDepartment",
				new Object[]{});
	}

	@Override
	public DataSet<Record> getDepartmentByName(String name)
	{
		return getExecutor("default").getDataSet(
				"SELECT FId, FName FROM TsDepartment WHERE FName = ?",
				new Object[]{name});
	}

	@Override
	public void createDepartment(UUID id, String name, UUID parentId)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{id, name, name, parentId, 1, 1, 0});
		getExecutor("default").executeBatch(
				"INSERT INTO TsDepartment (FId, FName, FFullName, FParentId, FEnabled, FTreeLevel, FIndex) VALUES (?,?,?,?,?,?,?)",
				args);
	}

	@Override
	public void updateDepartment(UUID id, String name, UUID parentId)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{name, name, parentId, id});
		getExecutor("default").executeBatch(
				"UPDATE TsDepartment SET FName=?, FFullName=?, FParentId=? WHERE FId=?",
				args);
	}

	// ── TsUser ─────────────────────────────────────────────────────────────────

	@Override
	public DataSet<Record> getAllEcpUsers()
	{
		return getExecutor("default").getDataSet(
				"SELECT FId, FName, FLoginName, FEmail, FDID, FEnabled, FIsServices, FDepartmentId FROM TsUser",
				new Object[]{});
	}

	@Override
	public DataSet<Record> getEcpUsersByDeptId(UUID deptId)
	{
		return getExecutor("default").getDataSet(
				"SELECT FId, FName, FLoginName, FEmail, FDID, FEnabled, FIsServices, FDepartmentId FROM TsUser WHERE FDepartmentId = ?",
				new Object[]{deptId});
	}

	@Override
	public Record getEcpUserByEmployeeId(String employeeId)
	{
		DataSet<Record> ds = getExecutor("default").getDataSet(
				"SELECT FId, FName, FLoginName, FEmail, FDID, FEnabled, FIsServices, FDepartmentId FROM TsUser WHERE FDID = ?",
				new Object[]{employeeId});
		return ds.isEmpty() ? null : ds.iterator().next();
	}

	@Override
	public void createEcpUser(UUID id, String name, String loginName, String email, UUID deptId, String employeeId)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{id, name, loginName, email, deptId, employeeId});
		getExecutor("default").executeBatch(
				"INSERT INTO TsUser (FId, FName, FLoginName, FEmail, FDepartmentId, FDID, FEnabled, FOnGuard) VALUES (?,?,?,?,?,?,1,1)",
				args);
	}

	@Override
	public void updateEcpUser(UUID id, String name, String loginName, String email, UUID deptId)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{name, loginName, email, deptId, id});
		getExecutor("default").executeBatch(
				"UPDATE TsUser SET FName=?, FLoginName=?, FEmail=?, FDepartmentId=?, FEnabled=1 WHERE FId=?",
				args);
	}

	@Override
	public void disableEcpUser(UUID id)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{id});
		getExecutor("default").executeBatch(
				"UPDATE TsUser SET FEnabled=0 WHERE FId=?",
				args);
	}

	// ── TsAccount ──────────────────────────────────────────────────────────────

	@Override
	public Record getAccountByLoginName(String loginName)
	{
		DataSet<Record> ds = getExecutor("default").getDataSet(
				"SELECT FId, FName, FLoginName, FEmail, FEnabled FROM TsAccount WHERE FLoginName = ?",
				new Object[]{loginName});
		return ds.isEmpty() ? null : ds.iterator().next();
	}

	@Override
	public void createAccount(UUID id, String name, String loginName, String password, String email)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{id, name, loginName, password, email});
		getExecutor("default").executeBatch(
				"INSERT INTO TsAccount (FId, FName, FLoginName, FPassword, FEmail, FCreateTime, FEnabled, FLanguage) VALUES (?,?,?,?,?,GETDATE(),1,'zh-tw')",
				args);
	}

	@Override
	public void updateAccount(UUID id, String name, String loginName, String email)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{name, loginName, email, id});
		getExecutor("default").executeBatch(
				"UPDATE TsAccount SET FName=?, FLoginName=?, FEmail=?, FEnabled=1 WHERE FId=?",
				args);
	}

	@Override
	public void disableAccount(UUID id)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{id});
		getExecutor("default").executeBatch(
				"UPDATE TsAccount SET FEnabled=0 WHERE FId=?",
				args);
	}

	// ── TsAccountIdentity ──────────────────────────────────────────────────────

	@Override
	public boolean hasAccountIdentity(UUID accountId)
	{
		DataSet<Record> ds = getExecutor("default").getDataSet(
				"SELECT 1 AS CNT FROM TsAccountIdentity WHERE FAccountId = ?",
				new Object[]{accountId});
		return !ds.isEmpty();
	}

	@Override
	public void createAccountIdentity(UUID id, String name, UUID accountId, UUID identityTypeId, UUID entityId)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{id, name, accountId, identityTypeId, entityId});
		getExecutor("default").executeBatch(
				"INSERT INTO TsAccountIdentity (FId, FName, FAccountId, FIdentityTypeId, FEntityId, FDefault, FIndex) VALUES (?,?,?,?,?,1,0)",
				args);
	}

	// ── TsRole / TsRoleUser ────────────────────────────────────────────────────

	@Override
	public DataSet<Record> getDefaultRoles()
	{
		return getExecutor("default").getDataSet(
				"SELECT FId, FName FROM TsRole WHERE FDefault=1",
				new Object[]{});
	}

	@Override
	public DataSet<Record> getSysAdminRoles()
	{
		return getExecutor("default").getDataSet(
				"SELECT FId, FName FROM TsRole WHERE FName LIKE N'%系統管理%'",
				new Object[]{});
	}

	@Override
	public boolean hasRoleAssigned(UUID roleId, UUID userId)
	{
		DataSet<Record> ds = getExecutor("default").getDataSet(
				"SELECT 1 AS CNT FROM TsRoleUser WHERE FRoleId=? AND FUserId=?",
				new Object[]{roleId, userId});
		return !ds.isEmpty();
	}

	@Override
	public void assignRoleToUser(UUID roleId, UUID userId)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{roleId, userId});
		getExecutor("default").executeBatch(
				"INSERT INTO TsRoleUser (FRoleId, FUserId) VALUES (?,?)",
				args);
	}
}