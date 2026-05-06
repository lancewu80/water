<%@page import="java.io.IOException"%>
<%@page import="java.nio.charset.Charset"%>
<%@page import="org.json.*"%>
<%@page import="org.apache.http.client.methods.CloseableHttpResponse"%>
<%@page import="org.apache.http.client.methods.HttpPost"%>
<%@page import="org.apache.http.impl.client.CloseableHttpClient"%>
<%@page import="org.apache.http.impl.client.HttpClients"%>
<%@page import="org.apache.http.entity.StringEntity"%>
<%@page import="org.apache.http.client.config.RequestConfig"%>
<%@page import="org.apache.http.util.EntityUtils"%>
<%@ page import="com.ai3.cus.ecpsso.SSOLoginLogHome" %>
<%@ page import="com.jeedsoft.quicksilver.base.type.ServiceContext" %>

<%
	response.setContentType("application/json; charset=UTF-8");
	boolean success = true;
	
//	String ecpUrl = request.getRequestURL().toString().replace("autoLogin_success.jsp", "");
//	String SSOUrl = ecpUrl + "openapi/TCBEcpSSO/SSOToken";
//	RequestConfig requestConfig = RequestConfig.custom().setSocketTimeout(5000).setConnectTimeout(5000).build();
	
//	JSONObject json = new JSONObject();
//	String content = request.getReader().readLine();
//	if (content != null) {
//        json = new JSONObject(content);
//    } else {
//		out.println("{\"success\":" + success + "}");
//		return;
//    }
	
//	HttpPost ECPPost = new HttpPost(SSOUrl);
//	ECPPost.setConfig(requestConfig);
//	ECPPost.setHeader("Accept-Language", "zh-tw");
//	ECPPost.setHeader("Content-Type", "application/json");
//	ECPPost.setEntity(new StringEntity(json.toString(), Charset.forName("UTF-8")));
//
//	try (CloseableHttpClient client = HttpClients.createDefault()) {
//		try (CloseableHttpResponse apiResponse = client.execute(ECPPost)) {
//			String result = EntityUtils.toString(apiResponse.getEntity(), "UTF-8");
//	JSONObject resultAnswer  = SSOLoginLogHome.getService().doSSOToken(ServiceContext.getDefaultInstance(), json);

			
//	if(resultAnswer.has("success")) {
//		success = resultAnswer.getBoolean("success");
//	}
//		} catch (Exception e) {
//		}
//	} catch (IOException e) {
//	}
//
	out.println("{\"success\":" + success + "}");
%>