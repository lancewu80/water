<%@page import="java.io.*,java.net.*,java.text.SimpleDateFormat,java.util.Date,java.util.Base64,org.json.*"%>
<%@ page import="javax.servlet.http.Cookie" %>
<%@ page import="com.ai3.cus.ecpsso.SSOLoginLogHome" %>
<%@ page import="com.jeedsoft.quicksilver.base.type.ServiceContext" %>
<%
response.setContentType("text/plain; charset=UTF-8");

String clientIP  = request.getRemoteAddr();
String userAgent = request.getHeader("User-Agent");
String language  = request.getParameter("language");
if (language == null || language.trim().isEmpty()) language = "zh-tw";

StringBuilder logBuf = new StringBuilder();
logBuf.append("\n========================================\n");
logBuf.append("[AUTOLOGIN REQUEST] ")
      .append(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS").format(new Date())).append("\n");
logBuf.append("  IP         : ").append(clientIP).append("\n");
logBuf.append("  User-Agent : ").append(userAgent).append("\n");
logBuf.append("  Method     : ").append(request.getMethod()).append("\n");

// ===== Step 2: Get PUBLIC_APP_USER_SSO_TOKEN from cookie =====
String waterToken = null;
Cookie[] cookies = request.getCookies();
if (cookies != null) {
    for (Cookie c : cookies) {
        if ("PUBLIC_APP_USER_SSO_TOKEN".equals(c.getName())) {
            waterToken = c.getValue();
            break;
        }
    }
}
logBuf.append("[STEP2] Cookie PUBLIC_APP_USER_SSO_TOKEN=").append(waterToken).append("\n");

String loginName = "";
String ai3Token  = "";
boolean success  = false;

try {
    if (waterToken == null || waterToken.trim().isEmpty()) {
        logBuf.append("[FAIL] 缺少 PUBLIC_APP_USER_SSO_TOKEN cookie\n");
    } else {
        // ===== Step 3: Call 3 Water SSO APIs → get APP_USER_LOGIN_ID =====
        logBuf.append("[STEP3] 呼叫 3 個 Water SSO APIs...\n");
        boolean waterOk = validate("", session, waterToken, logBuf);

        if (!waterOk) {
            logBuf.append("[FAIL] Water SSO 驗證失敗\n");
        } else {
            Object userLoginIdObj = session.getAttribute("userLoginId");
            loginName = (userLoginIdObj != null) ? userLoginIdObj.toString() : "";

            if (loginName.isEmpty()) {
                logBuf.append("[FAIL] Water SSO 未回傳有效的 APP_USER_LOGIN_ID\n");
            } else {
                logBuf.append("[STEP3] Water SSO SUCCESS loginName=").append(loginName).append("\n");

                // ===== Step 4: Call doSSO to get Ai3 SSO Token =====
                String empName = session.getAttribute("userChtName") != null
                                 ? session.getAttribute("userChtName").toString() : "";
                JSONObject doSSOInput = new JSONObject();
                doSSOInput.put("loginName", loginName);
                doSSOInput.put("empId",     loginName);
                doSSOInput.put("empName",   empName);
                doSSOInput.put("brName",    "");
                doSSOInput.put("brno",      "");

                logBuf.append("[STEP4-doSSO] input=").append(doSSOInput).append("\n");

                JSONObject doSSOResult = SSOLoginLogHome.getService().doSSO(
                        ServiceContext.getDefaultInstance(), doSSOInput);

                logBuf.append("[STEP4-doSSO] result=").append(doSSOResult).append("\n");

                if (doSSOResult != null && doSSOResult.optBoolean("success", false)) {
                    ai3Token  = doSSOResult.optString("token", "");
                    loginName = doSSOResult.optString("loginName", loginName);
                    logBuf.append("[STEP4-doSSO] SUCCESS loginName=").append(loginName)
                          .append("  ai3Token=").append(ai3Token).append("\n");
                    success = true;
                } else {
                    logBuf.append("[FAIL] doSSO 失敗或回傳 success=false\n");
                }
            }
        }
    }
} catch (Exception e) {
    logBuf.append("[ERROR] autologin flow exception: ")
          .append(e.getClass().getName()).append(": ").append(e.getMessage()).append("\n");
}

// ===== Step 5-6: Redirect to ECP autologin with loginName + ai3Token =====
// sso.jsp validates via doSSOToken; if fail → ECP falls back to AD login (Step 8)
String redirectUrl = buildAutoLoginUrl(request, loginName, ai3Token, language);
logBuf.append("[RESPONSE] success=").append(success).append("\n");
logBuf.append("[STEP5-REDIRECT] → ").append(redirectUrl).append("\n");
logBuf.append("========================================\n");

writeLog(application, logBuf.toString());

response.sendRedirect(redirectUrl);
%>

<%!
// ========== 常數 ==========
private static final String APP_PRIVATE_ID     = "b15174410df37d2f35538e6bd3ecef74";
private static final String APP_PRIVATE_PASSWD = "01d9ee5fea7951c3446f84a4b4039521";
private static final String LOG_FILE           = "sso_auth.log";

// ========== Step 3: Water SSO 3-API Validation → returns APP_USER_LOGIN_ID via session ==========
public boolean validate(String loginName,
                        HttpSession session,
                        String token,
                        StringBuilder log) {
    try {
        log.append("[STEP3-API] Start Water SSO 3-API validation\n");

        if (token == null || token.trim().isEmpty()) {
            log.append("[FAIL] token 為空,無法呼叫 SSO API\n");
            return false;
        }

        // ----- Step 3a: 取得 PRIVILEGED_APP_SSO_TOKEN -----
        String urlAuth  = "https://sso.water.gov.tw/app/request_basic_authentication/";
        String bodyAuth = "{"
            + "\"APP_PRIVATE_ID\":\""     + APP_PRIVATE_ID     + "\","
            + "\"APP_PRIVATE_PASSWD\":\"" + APP_PRIVATE_PASSWD + "\""
            + "}";

        log.append("[SSO-REQ1] URL=").append(urlAuth).append("\n");
        log.append("           BODY={\"APP_PRIVATE_ID\":\"").append(APP_PRIVATE_ID)
           .append("\",\"APP_PRIVATE_PASSWD\":\"***\"}\n");

        String resAuth = httpPost(urlAuth, bodyAuth, log);
        log.append("[SSO-RES1] ").append(resAuth).append("\n");

        if (resAuth == null) {
            log.append("[FAIL] Step3a request_basic_authentication 回應為 null\n");
            return false;
        }

        JSONObject auth = new JSONObject(resAuth);
        String ecAuth = auth.optString("ERROR_CODE", "N/A");
        if (!"0".equals(ecAuth)) {
            log.append("[FAIL] Step3a ERROR_CODE=").append(ecAuth)
               .append("  MSG=").append(auth.optString("ERROR_MSG", "")).append("\n");
            return false;
        }

        String privateAppToken = auth.optString("PRIVILEGED_APP_SSO_TOKEN", null);
        if (privateAppToken == null || privateAppToken.isEmpty()) {
            log.append("[FAIL] Step3a PRIVILEGED_APP_SSO_TOKEN 欄位缺失，完整回應: ").append(resAuth).append("\n");
            return false;
        }
        log.append("[SSO] Step3a 取得 PRIVILEGED_APP_SSO_TOKEN 成功\n");

        // ----- Step 3b: get_node_uuid -----
        String url2  = "https://sso.water.gov.tw/app_user/get_node_uuid/";
        String body2 = "{"
            + "\"PRIVILEGED_APP_SSO_TOKEN\":\""          + privateAppToken + "\","
            + "\"PUBLIC_APP_USER_SSO_TOKEN_TO_QUERY\":\"" + token + "\""
            + "}";

        log.append("[SSO-REQ2] URL=").append(url2).append("\n");
        log.append("           BODY=").append(body2).append("\n");

        String res2 = httpPost(url2, body2, log);
        log.append("[SSO-RES2] ").append(res2).append("\n");

        if (res2 == null) {
            log.append("[FAIL] Step3b get_node_uuid 回應為 null\n");
            return false;
        }

        JSONObject r = new JSONObject(res2);
        String ec2 = r.optString("ERROR_CODE", "N/A");
        if (!"0".equals(ec2)) {
            log.append("[FAIL] Step3b ERROR_CODE=").append(ec2)
               .append("  MSG=").append(r.optString("ERROR_MSG", "")).append("\n");
            return false;
        }

        String companyUuid = r.getString("APP_COMPANY_UUID");
        String userUuid    = r.getString("APP_USER_NODE_UUID");
        log.append("[SSO] Step3b companyUuid=").append(companyUuid)
           .append("  userUuid=").append(userUuid).append("\n");

        // ----- Step 3c: get_user_node → get APP_USER_LOGIN_ID -----
        String url3  = "https://sso.water.gov.tw/org_tree_surrogate/get_user_node/";
        String body3 = "{"
            + "\"PRIVILEGED_APP_SSO_TOKEN\":\""  + privateAppToken + "\","
            + "\"PUBLIC_APP_USER_SSO_TOKEN\":\"" + token           + "\","
            + "\"APP_COMPANY_UUID\":\""          + companyUuid     + "\","
            + "\"APP_USER_NODE_UUID\":\""        + userUuid        + "\","
            + "\"APP_USER_BASIC_PROFILE\":{"
            +   "\"APP_USER_LOGIN_ID\":\"\","
            +   "\"APP_USER_CHT_NAME\":\"\","
            +   "\"APP_USER_EMAIL\":\"\","
            +   "\"APP_DEPT_NODE_UUID\":\"\","
            +   "\"APP_USER_STATUS\":\"\""
            + "}"
            + "}";

        log.append("[SSO-REQ3] URL=").append(url3).append("\n");
        log.append("           BODY=").append(body3).append("\n");

        String res3 = httpPost(url3, body3, log);
        log.append("[SSO-RES3] ").append(res3).append("\n");

        if (res3 == null) {
            log.append("[FAIL] Step3c get_user_node 回應為 null\n");
            return false;
        }

        JSONObject u = new JSONObject(res3);
        String ec3 = u.optString("ERROR_CODE", "N/A");
        if (!"0".equals(ec3)) {
            log.append("[FAIL] Step3c ERROR_CODE=").append(ec3)
               .append("  MSG=").append(u.optString("ERROR_MSG", "")).append("\n");
            return false;
        }

        // ----- 取出 APP_USER_BASIC_PROFILE 欄位 -----
        JSONObject profile = u.getJSONObject("APP_USER_BASIC_PROFILE");

        String status       = profile.optString("APP_USER_STATUS",    "N/A");
        String userLoginId  = profile.optString("APP_USER_LOGIN_ID",  "");
        String userChtName  = profile.optString("APP_USER_CHT_NAME",  "");
        String userEmail    = profile.optString("APP_USER_EMAIL",     "");
        String deptNodeUuid = profile.optString("APP_DEPT_NODE_UUID", "");

        log.append("[SSO-PROFILE] STATUS=").append(status)
           .append("  LOGIN_ID=").append(userLoginId)
           .append("  CHT_NAME=").append(userChtName)
           .append("  EMAIL=").append(userEmail)
           .append("  DEPT_UUID=").append(deptNodeUuid)
           .append("\n");

        if (!"1".equals(status)) {
            log.append("[FAIL] 帳號狀態非啟用 status=").append(status).append("\n");
            return false;
        }

        // ----- 儲存 Water SSO profile 至 session (供 Step 4 使用) -----
        session.setAttribute("userLoginId",  userLoginId);
        session.setAttribute("userChtName",  userChtName);
        session.setAttribute("userEmail",    userEmail);
        session.setAttribute("deptNodeUuid", deptNodeUuid);
        session.setAttribute("userUuid",     userUuid);
        session.setAttribute("companyUuid",  companyUuid);

        log.append("[SSO] Step3 Water SSO validation SUCCESS  userLoginId=").append(userLoginId).append("\n");
        return true;

    } catch (Exception e) {
        log.append("[ERROR] validate() exception: ")
           .append(e.getClass().getName()).append(": ").append(e.getMessage()).append("\n");
        return false;
    }
}

// ========== HTTP POST 工具 ==========
private String httpPost(String urlStr, String body, StringBuilder log) {
    HttpURLConnection conn = null;
    try {
        URL url = new URL(urlStr);
        conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(15000);

        byte[] payload = body.getBytes("UTF-8");
        conn.getOutputStream().write(payload);

        int httpCode = conn.getResponseCode();
        if (httpCode != 200) {
            log.append("[ERROR] HTTP ").append(httpCode).append(" from ").append(urlStr).append("\n");
            return null;
        }

        BufferedReader br = new BufferedReader(
            new InputStreamReader(conn.getInputStream(), "UTF-8"));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) sb.append(line);
        br.close();
        return sb.toString();

    } catch (Exception e) {
        log.append("[ERROR] httpPost exception URL=").append(urlStr)
           .append("  ").append(e.getClass().getName()).append(": ").append(e.getMessage()).append("\n");
        return null;
    } finally {
        if (conn != null) conn.disconnect();
    }
}

// ========== Log 寫檔 ==========
private synchronized void writeLog(javax.servlet.ServletContext ctx, String content) {
    try {
        String logDir = ctx.getRealPath("/logs");
        if (logDir == null) logDir = System.getProperty("java.io.tmpdir");

        File dir = new File(logDir);
        if (!dir.exists()) dir.mkdirs();

        File logFile = new File(dir, LOG_FILE);
        try (FileWriter fw = new FileWriter(logFile, true)) {
            fw.write(content);
        }
    } catch (Exception e) {
        e.printStackTrace();
    }
}

private String buildAutoLoginUrl(javax.servlet.http.HttpServletRequest request, String loginName, String token, String language) {
    String base = request.getScheme()
        + "://"
        + request.getServerName()
        + ((request.getServerPort() == 80 || request.getServerPort() == 443) ? "" : ":" + request.getServerPort())
        + request.getContextPath()
        + "/openapi/user/autologin";
    String lang = (language == null || language.trim().isEmpty()) ? "zh-tw" : language;
    return base
        + "?token=" + encodeValue(token)
        + "&loginName=" + encodeValue(loginName)
        + "&language=" + encodeValue(lang);
}

private String encodeValue(String value) {
    try {
        return URLEncoder.encode(value == null ? "" : value, "UTF-8");
    } catch (Exception e) {
        return "";
    }
}
%>