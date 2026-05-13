package com.ai3.cus.ecpsso.api.impl;

import com.jeedsoft.quicksilver.base.api.impl.EntityApiImpl;
import com.jeedsoft.quicksilver.base.type.ApiContext;
import com.jeedsoft.quicksilver.base.type.JsonResult;
import com.jeedsoft.quicksilver.integration.annotation.Api;
import com.jeedsoft.quicksilver.integration.annotation.ApiAttribute;
import com.jeedsoft.quicksilver.integration.annotation.ApiDataType;

import java.io.IOException;

import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.ai3.cus.ecpsso.api.SSOLoginLogApi;
import com.ai3.cus.ecpsso.model.SSOLoginLogModel;
import com.ai3.cus.ecpsso.SSOLoginLogHome;

public class SSOLoginLogApiImpl extends EntityApiImpl<SSOLoginLogModel> implements SSOLoginLogApi
{
	private static final Logger logger = LoggerFactory.getLogger(SSOLoginLogApi.class);
	
	public SSOLoginLogApiImpl()
	{
		super(SSOLoginLogHome.UNIT_ID, SSOLoginLogModel.class);
	}
	
//	@Api(path = "/TCBEcpSSO/EcpSSO", isTokenRequired = false, input = {
//			@ApiAttribute(name = "SessionID", type = ApiDataType.STRING),
//	})
//	@Override
//	public JsonResult EcpSSO(ApiContext ac) throws IOException {
//		JSONObject args = ac.getRequestJson();
//		logger.info("[EcpSSO] args:" + args);
//		return SSOLoginLogHome.getService().doSSO(ac.getServiceContext(), args);
//	}
	
//	@Api(path = "/TCBEcpSSO/SSOToken", isTokenRequired = false, input = {
//			@ApiAttribute(name = "token", type = ApiDataType.STRING),
//	})
//	@Override
//	public JsonResult SSOToken(ApiContext ac) throws IOException {
//		JSONObject args = ac.getRequestJson();
//		logger.info("[SSOToken] args:" + args);
//		return SSOLoginLogHome.getService().doSSOToken(ac.getServiceContext(), args);
//	}
}
