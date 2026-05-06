<%@page import="java.io.*,java.net.URLEncoder,org.json.*"%>
<%
    String method = request.getMethod();
    String loginName = firstNonEmpty(request.getParameter("loginName"), request.getParameter("loginname"));
    String token = request.getParameter("token");
    String language = firstNonEmpty(request.getParameter("language"), "zh-tw");

    // 對外入口: 瀏覽器 GET 只做轉址，交由 ECP openapi 完成登入 session 建立
    if ("GET".equalsIgnoreCase(method)) {
        if (isBlank(loginName) || isBlank(token)) {
            response.setContentType("application/json; charset=UTF-8");
            out.println("{\"success\":false,\"message\":\"Missing loginName or token\"}");
            return;
        }
        String redirectUrl = request.getContextPath()
            + "/openapi/user/autologin?token=" + URLEncoder.encode(token, "UTF-8")
            + "&loginName=" + URLEncoder.encode(loginName, "UTF-8")
            + "&language=" + URLEncoder.encode(language, "UTF-8");
        response.sendRedirect(redirectUrl);
        return;
    }

    // 驗證入口: openapi 會以 POST 將 loginName/token 送到 verify URL，需回傳 {success:boolean}
    response.setContentType("application/json; charset=UTF-8");
    boolean success = false;
    String content = "";

    try {
        if (isBlank(loginName) || isBlank(token)) {
            BufferedReader reader = request.getReader();
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            content = sb.toString();
            if (!isBlank(content)) {
                JSONObject json = new JSONObject(content);
                if (isBlank(loginName)) {
                    loginName = firstNonEmpty(json.optString("loginName", ""), json.optString("loginname", ""));
                }
                if (isBlank(token)) {
                    token = json.optString("token", "");
                }
            }
        }

        success = valid(loginName, token);
        writeDebug(application, method, loginName, token, success, content);
    }
    catch (Exception e) {
        writeDebug(application, method, loginName, token, false, "EXCEPTION:" + e.getClass().getName());
        // 上線請維持靜默，避免外洩內部資訊
    }

    out.println("{\"success\":" + success + "}");
%>

<%! 
    public String firstNonEmpty(String first, String second) {
        return isBlank(first) ? second : first;
    }

    public boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    public String maskToken(String token) {
        if (isBlank(token)) {
            return "";
        }
        if (token.length() <= 8) {
            return "****";
        }
        return token.substring(0, 4) + "..." + token.substring(token.length() - 4);
    }

    public void writeDebug(javax.servlet.ServletContext context, String method, String loginName, String token, boolean success, String content) {
        try {
            String logPath = context.getRealPath("/custom/login/sso-debug.log");
            if (isBlank(logPath)) {
                logPath = System.getProperty("java.io.tmpdir") + File.separator + "ecp-sso-debug.log";
            }
            String bodyPreview = "";
            if (!isBlank(content)) {
                bodyPreview = content.replace("\r", " ").replace("\n", " ");
                if (bodyPreview.length() > 240) {
                    bodyPreview = bodyPreview.substring(0, 240) + "...";
                }
            }
            FileWriter fw = new FileWriter(logPath, true);
            fw.write(new java.util.Date().toString()
                + " | method=" + method
                + " | loginName=" + (loginName == null ? "null" : loginName)
                + " | token=" + maskToken(token)
                + " | success=" + success
                + " | hasBody=" + (!isBlank(content))
                + " | body=" + bodyPreview
                + "\n");
            fw.close();
        }
        catch (Exception ignore) {
        }
    }

    /**
     * TODO: 驗密邏輯
     */
    public Boolean valid(String loginName, String token) {
        // openapi 驗證回呼實際可能只帶 token，不帶 loginName
		return "abcdefghijklmnopqrstuvwxyz".equals(token);
    }
%>
