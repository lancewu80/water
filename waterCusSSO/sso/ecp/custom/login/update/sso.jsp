<%@page import="java.io.*,java.net.*,java.text.SimpleDateFormat,java.util.Date,org.json.*,javax.net.ssl.*,java.security.*,java.security.cert.*"%>
<%
response.setContentType("text/plain; charset=UTF-8");

// ===== 來源訊息 =====
String clientIP    = request.getRemoteAddr();
String userAgent   = request.getHeader("User-Agent");
String reqMethod   = request.getMethod();
String rawBody     = "";

String loginName = request.getParameter("loginName");

boolean success  = false;
String  errMsg   = "";

StringBuilder logBuf = new StringBuilder();
logBuf.append("\n========================================\n");
logBuf.append("[REQUEST] ")
      .append(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS").format(new Date())).append("\n");
logBuf.append("  IP         : ").append(clientIP).append("\n");
logBuf.append("  User-Agent : ").append(userAgent).append("\n");
logBuf.append("  Method     : ").append(reqMethod).append("\n");
logBuf.append("  loginName  : ").append(loginName).append("\n");

try {
    // GET 沒有才讀 JSON body
    if (loginName == null) {
        StringBuilder sb = new StringBuilder();
        BufferedReader reader = request.getReader();
        String line;
        while ((line = reader.readLine()) != null) sb.append(line);
        rawBody = sb.toString();

        logBuf.append("  rawBody    : ").append(rawBody).append("\n");

        if (!rawBody.isEmpty()) {
            JSONObject json = new JSONObject(rawBody);
            loginName = json.optString("loginName", null);
            logBuf.append("  [parsed] loginName=").append(loginName).append("\n");
        }
    }

    if (loginName == null) {
        errMsg = "loginName 為空";
        logBuf.append("[FAIL] ").append(errMsg).append("\n");
    } else {
        success = validate(loginName, session, logBuf);

        if (success) {
            session.setAttribute("isLogin",    true);
            session.setAttribute("loginUser",  loginName);
            session.setAttribute("loginName",  loginName);
            session.setAttribute("userId",     loginName);
            session.setAttribute("account",    loginName);
        }
    }

} catch (Exception e) {
    errMsg = e.getClass().getName() + ": " + e.getMessage();
    logBuf.append("[ERROR] main flow exception: ").append(errMsg).append("\n");
}

logBuf.append("[RESPONSE] success=").append(success).append("\n");
logBuf.append("========================================\n");

// 寫入 log 檔
writeLog(application, logBuf.toString());

out.print(success);
%>

<%!
// ========== 常數 ==========
// 台水 SSO 應用程式私鑰 (來源: 2026.05.04 AI客服SSO介接參數資訊.txt, APP_PUBLIC_ID=WATER_6268)
private static final String APP_PRIVATE_ID     = "b15174410df37d2f35538e6bd3ecef74";
private static final String APP_PRIVATE_PASSWD = "01d9ee5fea7951c3446f84a4b4039521";
private static final String LOG_FILE           = "sso_auth.log";

// ========== 核心驗證 ==========
public boolean validate(String loginName,
                        HttpSession session,
                        StringBuilder log) {
    try {
        log.append("[SSO] Start validation  loginName=").append(loginName).append("\n");

        // ----- Step 1: 取得 PUBLIC_APP_SSO_TOKEN -----
        String urlAuth  = "https://sso.water.gov.tw/app/request_basic_authentication/";
        String bodyAuth = "{"
            + "\"APP_PRIVATE_ID\":\""     + APP_PRIVATE_ID     + "\","
            + "\"APP_PRIVATE_PASSWD\":\"" + APP_PRIVATE_PASSWD + "\""
            + "}";

        log.append("[SSO-REQ1] URL=").append(urlAuth).append("\n");
        log.append("           BODY={\"APP_PRIVATE_ID\":\"").append(APP_PRIVATE_ID)
           .append("\",\"APP_PRIVATE_PASSWD\":\"***\"}\n");   // 密碼遮蔽

        String resAuth = httpPost(urlAuth, bodyAuth, log);
        log.append("[SSO-RES1] ").append(resAuth).append("\n");

        if (resAuth == null) {
            log.append("[FAIL] Step1 request_basic_authentication 回應為 null\n");
            return false;
        }

        JSONObject auth = new JSONObject(resAuth);
        String ecAuth = auth.optString("ERROR_CODE", "N/A");
        if (!"0".equals(ecAuth)) {
            log.append("[FAIL] Step1 ERROR_CODE=").append(ecAuth)
               .append("  MSG=").append(auth.optString("ERROR_MSG", "")).append("\n");
            return false;
        }

        String publicToken = auth.optString("PUBLIC_APP_SSO_TOKEN", null);
        String privateAppToken = auth.optString("PRIVILEGED_APP_SSO_TOKEN", null);
        if (publicToken == null || publicToken.isEmpty()) {
            log.append("[FAIL] Step1 PUBLIC_APP_SSO_TOKEN 欄位缺失或為空，完整回應: ").append(resAuth).append("\n");
            return false;
        }
        log.append("[SSO] Step1 取得 PUBLIC_APP_SSO_TOKEN 成功\n");

        // ----- Step 2: get_node_uuid -----
        String url2  = "https://sso.water.gov.tw/app_user/get_node_uuid/";
        String body2 = "{"
            + "\"PRIVILEGED_APP_SSO_TOKEN\":\""          + privateAppToken + "\","
            + "\"PUBLIC_APP_USER_SSO_TOKEN_TO_QUERY\":\"" + publicToken + "\""
            + "}";

        log.append("[SSO-REQ2] URL=").append(url2).append("\n");
        log.append("           BODY=").append(body2).append("\n");

        String res2 = httpPost(url2, body2, log);
        log.append("[SSO-RES2] ").append(res2).append("\n");

        if (res2 == null) {
            log.append("[FAIL] Step2 get_node_uuid 回應為 null\n");
            return false;
        }

        JSONObject r = new JSONObject(res2);
        String ec2 = r.optString("ERROR_CODE", "N/A");
        if (!"0".equals(ec2)) {
            log.append("[FAIL] Step2 ERROR_CODE=").append(ec2)
               .append("  MSG=").append(r.optString("ERROR_MSG", "")).append("\n");
            return false;
        }

        String companyUuid = r.getString("APP_COMPANY_UUID");
        String userUuid    = r.getString("APP_USER_NODE_UUID");
        log.append("[SSO] companyUuid=").append(companyUuid)
           .append("  userUuid=").append(userUuid).append("\n");

        // ----- Step 3: get_user_node -----
        String url3  = "https://sso.water.gov.tw/org_tree_surrogate/get_user_node/";
        String body3 = "{"
            + "\"PRIVILEGED_APP_SSO_TOKEN\":\""  + publicToken + "\","
            + "\"PUBLIC_APP_USER_SSO_TOKEN\":\"" + publicToken + "\","
            + "\"APP_COMPANY_UUID\":\""          + companyUuid + "\","
            + "\"APP_USER_NODE_UUID\":\""        + userUuid    + "\""
            + "}";

        log.append("[SSO-REQ3] URL=").append(url3).append("\n");
        log.append("           BODY=").append(body3).append("\n");

        String res3 = httpPost(url3, body3, log);
        log.append("[SSO-RES3] ").append(res3).append("\n");

        if (res3 == null) {
            log.append("[FAIL] Step3 get_user_node 回應為 null\n");
            return false;
        }

        JSONObject u = new JSONObject(res3);
        String ec3 = u.optString("ERROR_CODE", "N/A");
        if (!"0".equals(ec3)) {
            log.append("[FAIL] Step3 ERROR_CODE=").append(ec3)
               .append("  MSG=").append(u.optString("ERROR_MSG", "")).append("\n");
            return false;
        }

        // ----- Step 4: 狀態檢查 -----
        JSONObject profile = u.getJSONObject("APP_USER_BASIC_PROFILE");
        String status = profile.optString("APP_USER_STATUS", "N/A");
        log.append("[SSO] APP_USER_STATUS=").append(status).append("\n");

        if (!"1".equals(status)) {
            log.append("[FAIL] 帳號狀態非啟用 status=").append(status).append("\n");
            return false;
        }

        // ----- Step 5: 寫入 session -----
        session.setAttribute("loginUser",    loginName);
        session.setAttribute("userUuid",     userUuid);
        session.setAttribute("companyUuid",  companyUuid);

        log.append("[SSO] Validation SUCCESS\n");
        return true;

    } catch (Exception e) {
        log.append("[ERROR] validate() exception: ")
           .append(e.getClass().getName()).append(": ").append(e.getMessage()).append("\n");
        return false;
    }
}

// ========== 略過 SSL 憑證驗證 (僅限測試環境) ==========
private static SSLSocketFactory TRUST_ALL_SSL_FACTORY = null;
private static HostnameVerifier  TRUST_ALL_HV         = null;

private synchronized void initTrustAll() {
    if (TRUST_ALL_SSL_FACTORY != null) return;
    try {
        TrustManager[] trustAll = new TrustManager[] {
            new X509TrustManager() {
                public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
                public void checkClientTrusted(X509Certificate[] c, String a) {}
                public void checkServerTrusted(X509Certificate[] c, String a) {}
            }
        };
        SSLContext sc = SSLContext.getInstance("TLS");
        sc.init(null, trustAll, new java.security.SecureRandom());
        TRUST_ALL_SSL_FACTORY = sc.getSocketFactory();
        TRUST_ALL_HV = new HostnameVerifier() {
            public boolean verify(String hostname, SSLSession session) { return true; }
        };
    } catch (Exception e) {
        e.printStackTrace();
    }
}

// ========== HTTP POST 工具 ==========
private String httpPost(String urlStr, String body, StringBuilder log) {
    HttpURLConnection conn = null;
    try {
        initTrustAll();

        URL url = new URL(urlStr);
        conn = (HttpURLConnection) url.openConnection();

        // 若為 HTTPS 則套用信任全部憑證
        if (conn instanceof HttpsURLConnection) {
            HttpsURLConnection https = (HttpsURLConnection) conn;
            https.setSSLSocketFactory(TRUST_ALL_SSL_FACTORY);
            https.setHostnameVerifier(TRUST_ALL_HV);
        }

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
%>
