<%@ page language="java" contentType="application/json; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ page import="org.json.*,javax.naming.*,javax.naming.directory.*,java.util.*"%>
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
    StringBuilder sb = new StringBuilder();
    String line;

    try {
        // 讀取 Body 內容 (處理多行讀取確保 JSON 完整)
        java.io.BufferedReader reader = request.getReader();
        while ((line = reader.readLine()) != null) {
            sb.append(line);
        }

        String content = sb.toString();

        if (content != null && !content.isEmpty()) {
            JSONObject json = new JSONObject(content);
            loginName = json.optString("loginName");
            password = json.optString("password");

            // 執行 LDAP 驗證
            if (!loginName.isEmpty() && !password.isEmpty()) {
                success = valid(loginName, password);
            }
        }

        // 登入成功，設定 Session
        if (success) {
            session.setAttribute("isLogin", true);
            session.setAttribute("loginUser", loginName);
        }

    } catch (Exception e) {
        // 測試環境輸出 Log，正式環境應記錄到 Log File
        e.printStackTrace();
    }

    // 回傳 JSON 結果
    out.print("{\"success\":" + success + "}");
    out.flush();
%>

<%!
    /**
     * LDAP 驗證邏輯
     */
    public Boolean valid(String loginName, String password) {
        DirContext ctx = null;
        try {
            String ldapUrl = "ldaps://10.100.1.215:636";
            // 根據你的 AD 網域調整 DN 格式
            String userDN = loginName + "@hubhq.water.gov.tw";

            Hashtable<String, String> env = new Hashtable<>();
            env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
            env.put(Context.PROVIDER_URL, ldapUrl);
            env.put(Context.SECURITY_AUTHENTICATION, "simple");
            env.put(Context.SECURITY_PRINCIPAL, userDN);
            env.put(Context.SECURITY_CREDENTIALS, password);

            // 嘗試建立連線，若密碼錯誤會拋出 Exception
            ctx = new InitialDirContext(env);
            return true;

        } catch (Exception e) {
            System.out.println("LDAP Login Failed for user: " + loginName);
            e.printStackTrace();
            return false;
        } finally {
            if (ctx != null) {
                try {
                    ctx.close();
                } catch (NamingException e) {
                    // Ignore
                }
            }
        }
    }
%>