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
		return getExecutor("default").getDataSet(
				"SELECT EMPLOYEEID, DISPLAYNAME, EMAILADDRESS, LOGINID, DEPARTMENTID FROM v_KM_USER WHERE LEFT(DEPARTMENTID, 2) = '00'",
				new Object[]{});
	}

	@Override
	public DataSet<Record> getItDeptList()
	{
		return getExecutor("default").getDataSet(
				"SELECT DEPARTMENTID FROM v_KM_DEPT WHERE DISPLAYNAME LIKE N'%資訊%'",
				new Object[]{});
	}

	// ── TsDepartment ───────────────────────────────────────────────────────────

	@Override
	public DataSet<Record> getDepartmentByName(String name)
	{
		return getExecutor("default").getDataSet(
				"SELECT FId, FName FROM TsDepartment WHERE FName = ?",
				new Object[]{name});
	}

	@Override
	public void createDepartment(UUID id, String name)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{id, name, name, 1, 1, 0});
		getExecutor("default").executeBatch(
				"INSERT INTO TsDepartment (FId, FName, FFullName, FEnabled, FTreeLevel, FIndex) VALUES (?,?,?,?,?,?)",
				args);
	}

	// ── TsUser ─────────────────────────────────────────────────────────────────

	@Override
	public DataSet<Record> getEcpUsersByDeptId(UUID deptId)
	{
		return getExecutor("default").getDataSet(
				"SELECT FId, FName, FLoginName, FEmail, FDID, FEnabled, FIsServices FROM TsUser WHERE FDepartmentId = ?",
				new Object[]{deptId});
	}

	@Override
	public Record getEcpUserByEmployeeId(String employeeId)
	{
		DataSet<Record> ds = getExecutor("default").getDataSet(
				"SELECT FId, FName, FLoginName, FEmail, FDID, FEnabled, FIsServices FROM TsUser WHERE FDID = ?",
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
	public void updateEcpUser(UUID id, String name, String loginName, String email)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{name, loginName, email, id});
		getExecutor("default").executeBatch(
				"UPDATE TsUser SET FName=?, FLoginName=?, FEmail=?, FEnabled=1 WHERE FId=?",
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
	public void createAccount(UUID id, String name, String loginName, String email)
	{
		List<Object[]> args = new ArrayList<>();
		args.add(new Object[]{id, name, loginName, email});
		getExecutor("default").executeBatch(
				"INSERT INTO TsAccount (FId, FName, FLoginName, FPassword, FEmail, FCreateTime, FEnabled, FLanguage) VALUES (?,?,?,'1',?,GETDATE(),1,'zh-tw')",
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