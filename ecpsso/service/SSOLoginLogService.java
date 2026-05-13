package com.ai3.cus.ecpsso.service;

import com.jeedsoft.quicksilver.base.service.EntityService;
import com.jeedsoft.quicksilver.base.type.ServiceContext;

import java.io.IOException;

import org.json.JSONObject;
import com.ai3.cus.ecpsso.model.SSOLoginLogModel;

public interface SSOLoginLogService extends EntityService<SSOLoginLogModel>
{
	public JSONObject doSSO(ServiceContext sc, JSONObject args) throws IOException;
	public JSONObject checkUser(ServiceContext sc, JSONObject args, JSONObject obj);
	public void addLog(ServiceContext sc, JSONObject args, JSONObject obj);
	public JSONObject doSSOToken(ServiceContext sc, JSONObject args) throws IOException;
}
