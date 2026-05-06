<%@page import="java.util.Base64"%>
<%@page import="java.io.IOException"%>
<%@page import="java.nio.charset.Charset"%>
<%@page import="org.json.*"%>
<%@page import="org.json.JSONException"%>
<%@page import="org.apache.http.client.methods.CloseableHttpResponse"%>
<%@page import="org.apache.http.client.methods.HttpPost"%>
<%@page import="org.apache.http.impl.client.CloseableHttpClient"%>
<%@page import="org.apache.http.impl.client.HttpClients"%>
<%@page import="org.apache.http.entity.StringEntity"%>
<%@page import="org.apache.http.client.config.RequestConfig"%>
<%@page import="org.apache.http.util.EntityUtils"%>
<%@ page import="com.ai3.cus.ecpsso.SSOLoginLogHome" %>
<%@ page import="com.jeedsoft.quicksilver.base.type.ServiceContext" %>
<%@ page import="com.jeedsoft.quicksilver.base.type.JsonResult" %>

<%
	response.setContentType("application/json; charset=UTF-8");
	boolean success = false;
	
	String ecpUrl = request.getRequestURL().toString().replace("autoLogin.jsp", "");
//	String SSOUrl = ecpUrl + "openapi/TCBEcpSSO/EcpSSO";
	String successUrl = ecpUrl + "autoLogin_success.jsp";
//	RequestConfig requestConfig = RequestConfig.custom().setSocketTimeout(5000).setConnectTimeout(5000).build();
	
//	String SessionID = "";
	String sessionHeader = request.getHeader("x-userinfo").replace("-", "+").replace("_", "/");
	
	JSONObject json = new JSONObject();
	json.put("SessionID", sessionHeader);

//	HttpPost ECPPost = new HttpPost(SSOUrl);
//	ECPPost.setConfig(requestConfig);
//	ECPPost.setHeader("Accept-Language", "zh-tw");
//	ECPPost.setHeader("Content-Type", "application/json");
//	ECPPost.setEntity(new StringEntity(json.toString(), Charset.forName("UTF-8")));
	JSONObject resultAnswer = SSOLoginLogHome.getService().doSSO(ServiceContext.getDefaultInstance(), json);
	if(resultAnswer.has("success")) {
		success = resultAnswer.getBoolean("success");
		if(success) {
			String empId = resultAnswer.getString("empId");
			String token = resultAnswer.getString("token");
			String loginUrl = ecpUrl + "openapi/user/autologin?token=" + token + "&loginName=" + empId + "&language=zh-tw";
			response.sendRedirect(loginUrl);
			return;
		}
	}
	response.sendRedirect(successUrl);
%>