<%@page import="org.json.*,java.io.*,java.text.SimpleDateFormat,java.util.Date"%>
<%@ page import="com.jeedsoft.quicksilver.base.type.ServiceContext" %>
<%@ page import="com.ai3.cus.ecpsso.SSOLoginLogHome" %>
<%
    response.setContentType("application/json; charset=UTF-8");

    boolean success  = false;
    String loginName = "";
    String token     = "";
    String content   = "";

    StringBuilder logBuf = new StringBuilder();
    logBuf.append("\n========================================\n");
    logBuf.append("[SSO REQUEST] ")
          .append(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS").format(new Date())).append("\n");
    logBuf.append("  IP         : ").append(request.getRemoteAddr()).append("\n");
    logBuf.append("  Method     : ").append(request.getMethod()).append("\n");

    try {
        // Read full body (multi-line safe)
        StringBuilder sb = new StringBuilder();
        String line;
        java.io.BufferedReader reader = request.getReader();
        while ((line = reader.readLine()) != null) sb.append(line);
        content = sb.toString();

        logBuf.append("  rawBody    : ").append(content).append("\n");

        JSONObject json = new JSONObject(content);
        loginName = json.optString("loginName", "");
        token     = json.optString("token", "");

        logBuf.append("  loginName  : ").append(loginName).append("\n");
        logBuf.append("  token      : ").append(token).append("\n");

        // ===== Step 7: Validate Ai3 SSO Token via doSSOToken =====
        logBuf.append("[STEP7-doSSOToken] Calling doSSOToken...\n");

        JSONObject resultAnswer = SSOLoginLogHome.getService().doSSOToken(
                ServiceContext.getDefaultInstance(), json);

        logBuf.append("[STEP7-doSSOToken] result=").append(resultAnswer).append("\n");

        if (resultAnswer != null && resultAnswer.has("success")) {
            success = resultAnswer.getBoolean("success");
        }

        if (success) {
            logBuf.append("[STEP7] doSSOToken SUCCESS → 登入 ECP\n");
        } else {
            // Step 8: ECP frontend falls back to AD login on success=false
            logBuf.append("[STEP8] doSSOToken FAIL → ECP 改用 AD login\n");
        }

    } catch (Exception e) {
        logBuf.append("[ERROR] sso.jsp exception: ")
              .append(e.getClass().getName()).append(": ").append(e.getMessage()).append("\n");
    }

    logBuf.append("[RESPONSE] success=").append(success).append("\n");
    logBuf.append("========================================\n");

    writeLog(application, logBuf.toString());

    out.println("{\"success\":" + success + "}");
%>

<%!
    private static final String LOG_FILE = "sso_auth.log";

    private synchronized void writeLog(javax.servlet.ServletContext ctx, String content) {
        try {
            String logDir = ctx.getRealPath("/logs");
            if (logDir == null) logDir = System.getProperty("java.io.tmpdir");

            java.io.File dir = new java.io.File(logDir);
            if (!dir.exists()) dir.mkdirs();

            java.io.File logFile = new java.io.File(dir, LOG_FILE);
            try (java.io.FileWriter fw = new java.io.FileWriter(logFile, true)) {
                fw.write(content);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
%>
