<%@ page language="java" contentType="application/json; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ page import="org.json.*,javax.naming.*,javax.naming.directory.*,java.util.*,java.io.*,java.text.SimpleDateFormat"%>
<%
    /**
     * 1. 解決 CORS 跨網域問題
     * 允許來自本地檔案 (file://) 或其他 Origin 的請求
     */
    response.setHeader("Access-Control-Allow-Origin", "*");
    response.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
    response.setHeader("Access-Control-Allow-Headers", "Content-Type");

    // 設定回傳格式為 JSON
    response.setContentType("application/json; charset=UTF-8");

    // 處理瀏覽器的預檢請求 (Preflight Request)
    if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
        response.setStatus(HttpServletResponse.SC_OK);
        return;
    }

    boolean success = false;
    String loginName = "";
    String password = "";
    String content = "";
    StringBuilder sb = new StringBuilder();
    String line;

    // ===== LOG: 初始化 =====
    StringBuilder logBuf = new StringBuilder();
    logBuf.append("\n========================================\n");
    logBuf.append("[REQUEST] ")
          .append(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS").format(new java.util.Date())).append("\n");

    // ===== LOG: INPUT =====
    logBuf.append("--- INPUT ---\n");
    logBuf.append("  IP          : ").append(request.getRemoteAddr()).append("\n");
    logBuf.append("  User-Agent  : ").append(request.getHeader("User-Agent")).append("\n");
    logBuf.append("  Method      : ").append(request.getMethod()).append("\n");
    logBuf.append("  ContentType : ").append(request.getContentType()).append("\n");

    try {
        // 讀取 Body 內容 (處理多行讀取確保 JSON 完整)
        java.io.BufferedReader reader = request.getReader();
        while ((line = reader.readLine()) != null) {
            sb.append(line);
        }
        content = sb.toString();

        logBuf.append("  rawBody     : ").append(content).append("\n");

        // ===== LOG: PROCESSING =====
        logBuf.append("--- PROCESSING ---\n");

        if (content != null && !content.isEmpty()) {
            JSONObject json = new JSONObject(content);
            loginName = json.optString("loginName");
            password  = json.optString("password");

            logBuf.append("  loginName   : ").append(loginName).append("\n");
            logBuf.append("  password    : ").append(password.isEmpty() ? "(empty)" : "******").append("\n");

            // 執行 LDAP 驗證
            if (!loginName.isEmpty() && !password.isEmpty()) {
                logBuf.append("  [LDAP] 開始驗證 loginName=").append(loginName).append("\n");
                success = valid(loginName, password, logBuf);
                logBuf.append("  [LDAP] 驗證結果=").append(success).append("\n");
            } else {
                logBuf.append("  [SKIP] loginName 或 password 為空，跳過 LDAP 驗證\n");
            }
        } else {
            logBuf.append("  [SKIP] Body 為空，跳過解析\n");
        }

        // 登入成功，設定 Session
        if (success) {
            session.setAttribute("isLogin", true);
            session.setAttribute("loginUser", loginName);
            logBuf.append("  [SESSION] isLogin=true  loginUser=").append(loginName).append("\n");
        }

    } catch (Exception e) {
        logBuf.append("  [ERROR] Exception: ").append(e.getClass().getName())
              .append(": ").append(e.getMessage()).append("\n");
        e.printStackTrace();
    }

    // ===== LOG: OUTPUT =====
    String responseBody = "{\"success\":" + success + "}";
    logBuf.append("--- OUTPUT ---\n");
    logBuf.append("  response    : ").append(responseBody).append("\n");
    logBuf.append("========================================\n");

    // 寫入 log 檔
    writeLoginLog(application, logBuf.toString());

    // 回傳 JSON 結果
    out.print(responseBody);
    out.flush();
%>

<%!
    private static final String LOGIN_LOG_FILE = "login_auth.log";

    /**
     * LDAP 驗證邏輯（附 log）
     */
    public Boolean valid(String loginName, String password, StringBuilder log) {
        DirContext ctx = null;
        try {
            String ldapUrl = "ldaps://10.100.1.215:636";
            String userDN  = loginName + "@hubhq.water.gov.tw";

            log.append("  [LDAP] URL=").append(ldapUrl).append("\n");
            log.append("  [LDAP] principal=").append(userDN).append("\n");

            Hashtable<String, String> env = new Hashtable<>();
            env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
            env.put(Context.PROVIDER_URL, ldapUrl);
            env.put(Context.SECURITY_AUTHENTICATION, "simple");
            env.put(Context.SECURITY_PRINCIPAL, userDN);
            env.put(Context.SECURITY_CREDENTIALS, password);

            // 嘗試建立連線，若密碼錯誤會拋出 Exception
            ctx = new InitialDirContext(env);
            log.append("  [LDAP] 連線成功\n");
            return true;

        } catch (Exception e) {
            log.append("  [LDAP] 驗證失敗: ").append(e.getClass().getName())
               .append(": ").append(e.getMessage()).append("\n");
            return false;
        } finally {
            if (ctx != null) {
                try {
                    ctx.close();
                    log.append("  [LDAP] Context 已關閉\n");
                } catch (NamingException e) {
                    // Ignore
                }
            }
        }
    }

    /**
     * 寫入 log 檔
     */
    private synchronized void writeLoginLog(javax.servlet.ServletContext ctx, String content) {
        try {
            String logDir = ctx.getRealPath("/logs");
            if (logDir == null) logDir = System.getProperty("java.io.tmpdir");

            java.io.File dir = new java.io.File(logDir);
            if (!dir.exists()) dir.mkdirs();

            java.io.File logFile = new java.io.File(dir, LOGIN_LOG_FILE);
            try (java.io.FileWriter fw = new java.io.FileWriter(logFile, true)) {
                fw.write(content);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
%>