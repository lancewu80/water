package com.ai3.cus.ecpsso.dao.impl;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.jeedsoft.common.advanced.db.dataset.Record;
import com.jeedsoft.quicksilver.base.dao.impl.EntityDaoImpl;
import com.jeedsoft.quicksilver.base.type.DaoContext;
import com.ai3.cus.ecpsso.dao.SSOLoginLogDao;
import com.ai3.cus.ecpsso.model.SSOLoginLogModel;
import com.ai3.cus.ecpsso.SSOLoginLogHome;

public class SSOLoginLogDaoImpl extends EntityDaoImpl<SSOLoginLogModel> implements SSOLoginLogDao
{
	private static final Logger logger = LoggerFactory.getLogger(SSOLoginLogDaoImpl.class);

	public SSOLoginLogDaoImpl()
	{
		super(SSOLoginLogHome.UNIT_ID, SSOLoginLogModel.class);
	}
	@Override
	public Record getUserItem(DaoContext dc, String loginName) {
		String sql = "select u.FId as FId, u.FDepartmentId as FDepartmentId "
				+ "from TsUser u "
				+ "inner join TsAccountIdentity ai on ai.FEntityId = u.FId "
				+ "inner join TsAccount a on ai.FAccountId = a.FId "
				+ "where a.FLoginName=?";
		logger.debug("[getUserItem] input.loginName:{}, sql:{}", loginName, sql);
		Record userItem = getExecutor("default").getRecord(sql, loginName);
		logger.debug("[getUserItem] output:{}", userItem);
		return userItem;
	}
	@Override
	public Record getAccountIdentity(DaoContext dc, String entityId) {
		String sql = "select FAccountId from TsAccountIdentity where FEntityId=?";
		logger.debug("[getAccountIdentity] input.entityId:{}, sql:{}", entityId, sql);
		Record accountIdentity = getExecutor("default").getRecord(sql, entityId);
		logger.debug("[getAccountIdentity] output:{}", accountIdentity);
		return accountIdentity;
	}
	@Override
	public Record getSSOToken(DaoContext dc, String token, String empId) {
		String sql = "select FId from TpCUSmLoginLog where FName = 'success' and FCreateTime >= dateadd('minute', -5, timestamp(getDate())) and U_token=? and U_CreateUserName=?";
		logger.debug("[getSSOToken] input.token:{}, input.empId:{}, sql:{}", token, empId, sql);
		Record ssoToken = getExecutor("default").getRecord(sql, token, empId);
		logger.debug("[getSSOToken] output:{}", ssoToken);
		return ssoToken;
	}
}
