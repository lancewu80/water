package com.ai3.cus.ecpsso.service.impl;

import com.chainsea.ecp.common.util.CommonUtil;
import com.jeedsoft.common.advanced.db.dataset.Record;
import com.jeedsoft.common.basic.util.JsonUtil;
import com.jeedsoft.quicksilver.base.service.impl.EntityServiceImpl;
import com.jeedsoft.quicksilver.base.type.DaoContext;
import com.jeedsoft.quicksilver.base.type.ServiceContext;
import com.jeedsoft.quicksilver.i18n.LanguageHome;

import java.io.IOException;
import java.util.UUID;

import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.ai3.cus.ecpsso.service.SSOLoginLogService;
import com.chainsea.ecp.user.api.util.UserApiUtil;
import com.ai3.cus.ecpsso.SSOLoginLogHome;
import com.ai3.cus.ecpsso.model.SSOLoginLogModel;

public class SSOLoginLogServiceImpl extends EntityServiceImpl<SSOLoginLogModel> implements SSOLoginLogService
{
	private static final Logger logger = LoggerFactory.getLogger(SSOLoginLogService.class);
	
	public SSOLoginLogServiceImpl()
	{
		super(SSOLoginLogHome.UNIT_ID, SSOLoginLogModel.class);
	}
	// 1.網址缺少參數	=> LoginStatus=failed
	// 2.登入成功		=> LoginStatus=true
	// 3.其他(資料錯誤、ECP驗證失敗等等)			=> LoginStatus=false
	// args format: {"empId":"...","loginName":"...","empName":"...","brName":"...","brno":"..."}
	@Override
	public JSONObject doSSO(ServiceContext sc, JSONObject args) throws IOException {
		logger.debug("[doSSO] args:{}", args);
		JSONObject obj = new JSONObject();
		obj.put("success", false);
		obj.put("LoginStatus", "false");
		
		try {
			if (args.has("empId") && args.has("loginName")) {
				obj.put("empId", JsonUtil.getString(args, "empId", ""));
				obj.put("empName", JsonUtil.getString(args, "empName", ""));
				obj.put("brno", JsonUtil.getString(args, "brno", ""));
				obj.put("brName", JsonUtil.getString(args, "brName", ""));
				obj.put("loginName", JsonUtil.getString(args, "loginName", ""));
				logger.debug("[doSSO] checkUser.obj:{}", obj);

				JSONObject resultUser = checkUser(sc, args, obj);
				if (resultUser.getBoolean("hasData")) {
					obj.put("FUserId", resultUser.getString("FUserId"));
					obj.put("FDepartmentId", resultUser.getString("FDepartmentId"));
					
					obj.put("success", true);
					obj.put("LoginStatus", "success");
					obj.put("token", UUID.randomUUID().toString());
				}
			} else {
				obj.put("LoginStatus", "failed. No input empId or loginName.");
			}
		} catch (Exception e) {
			logger.error("[doSSO] Error:{}", CommonUtil.extractExceptionMessage(e));
		}
		addLog(sc, args, obj);
		
		logger.debug("[doSSO] obj:{}", obj);
		return obj;
	}
	
	// ECP有無這筆資料
	@Override
	public JSONObject checkUser(ServiceContext sc, JSONObject args, JSONObject obj) {
		logger.debug("[checkUser] sc:{}, args:{}, obj:{}", sc, args, obj);
		DaoContext dc = sc.getDaoContext();
		JSONObject result = new JSONObject();
		result.put("hasData", false);
		
		String empId = "";
		String loginName = "";
		try {
			empId = obj.getString("empId");
			loginName = obj.getString("loginName");
			
			Record UserItem = SSOLoginLogHome.getDao().getUserItem(dc, loginName);
			if (UserItem != null) {
				logger.debug("[checkUser] UserItem:{}", UserItem);
				result.put("FUserId", UserItem.getUuid("FId").toString());
				result.put("FDepartmentId", UserItem.getUuid("FDepartmentId").toString());
				result.put("hasData", true);
			}
			
			logger.debug("[checkUser] result:{}", result);
		} catch (Exception e) {
			logger.error("[checkUser] Error:{}", CommonUtil.extractExceptionMessage(e));
		}
		
		return result;
	}
	
	// SSO登入紀錄
	@Override
	public void addLog(ServiceContext sc, JSONObject args, JSONObject obj) {
		logger.debug("[addLog] add CUS.SSOLoginLog sc:{}, args:{}, obj:{}", sc, args, obj);
		SSOLoginLogModel model = new SSOLoginLogModel();
		model.put("U_SessionID", JsonUtil.getString(args, "SessionID", ""));	//SessionID
		model.put("U_token", JsonUtil.getString(obj, "token", ""));	//token
		model.put("FName", JsonUtil.getString(obj, "LoginStatus", ""));	//登入狀態
		model.put("FCreateUserId", JsonUtil.getString(obj, "FUserId", "")); //員工ID
		model.put("FCreateDepartmentId", JsonUtil.getString(obj, "FDepartmentId", "")); //部門ID
		model.put("U_CreateUserName", JsonUtil.getString(obj, "empId", "")); //員工編號
		model.put("U_CreateDepartment", JsonUtil.getString(obj, "brName", "")); //部門名稱
		
		ServiceContext newsc = new ServiceContext(UserApiUtil.TOKEN_API_USER_ID, LanguageHome.EN_US);
		try {
			UUID userID = SSOLoginLogHome.getService().create(newsc, model);
			logger.debug("[addLog] addLog:{}", userID);
		} catch (Exception e) {
			logger.error("[addLog] Error:{}", CommonUtil.extractExceptionMessage(e));
		}
	}
	
	// 1.token驗證失敗	=> LoginStatus=token false
	@Override
	public JSONObject doSSOToken(ServiceContext sc, JSONObject args) throws IOException {
		logger.debug("[doSSOToken] args: {}",  args);
		DaoContext dc = sc.getDaoContext();
		JSONObject obj = new JSONObject();
		obj.put("success", false);
		
		try {
			String token = JsonUtil.getString(args, "token", "");
			String empId = JsonUtil.getString(args, "loginName", "");
			Record hasToken = SSOLoginLogHome.getDao().getSSOToken(dc, token, empId);
			if (hasToken != null) {
				obj.put("success", true);
			}
		} catch (Exception e) {
			logger.error("[doSSOToken] Error: {}", CommonUtil.extractExceptionMessage(e));
		}
		
		logger.debug("[doSSOToken] obj: {}", obj);
		return obj;
	}
}
