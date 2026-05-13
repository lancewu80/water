package com.ai3.cus.ecpsso.action.impl;

import com.jeedsoft.quicksilver.base.action.impl.EntityActionImpl;
import com.jeedsoft.quicksilver.base.type.ActionContext;
import com.jeedsoft.quicksilver.base.type.JsonResult;

import java.io.IOException;
import org.json.JSONObject;

import com.ai3.cus.ecpsso.action.SSOLoginLogAction;
import com.ai3.cus.ecpsso.model.SSOLoginLogModel;
import com.ai3.cus.ecpsso.SSOLoginLogHome;

public class SSOLoginLogActionImpl extends EntityActionImpl<SSOLoginLogModel> implements SSOLoginLogAction
{
	public SSOLoginLogActionImpl()
	{
		super(SSOLoginLogHome.UNIT_ID, SSOLoginLogModel.class);
	}
//	@Override
//	public JsonResult EcpSSO(ActionContext ac) throws IOException {
//		JSONObject args = ac.getArguments();
//		return SSOLoginLogHome.getService().doSSO(ac.getServiceContext(), args);
//	}
}
