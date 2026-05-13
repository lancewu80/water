package com.ai3.cus.ecpsso.dao;

import com.jeedsoft.common.advanced.db.dataset.Record;
import com.jeedsoft.quicksilver.base.dao.EntityDao;
import com.jeedsoft.quicksilver.base.type.DaoContext;
import com.ai3.cus.ecpsso.model.SSOLoginLogModel;

public interface SSOLoginLogDao extends EntityDao<SSOLoginLogModel>
{
	Record getUserItem(DaoContext dc, String loginName);
	Record getAccountIdentity(DaoContext dc, String entityId);
	Record getSSOToken(DaoContext dc, String token, String empId);
}
