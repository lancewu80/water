<%@page import="java.io.*,java.net.*,org.json.*"%>
<%
response.setContentType("application/json; charset=UTF-8");

boolean success = false;
String loginName = "";
String token = "";
String content = "";

try {
    content = request.getReader().readLine();
    JSONObject json = new JSONObject(content);

    loginName = json.getString("loginName");
    token = json.getString("token");

    success = valid(loginName, token, session);

    if (success) {
        session.setAttribute("isLogin", true);
    }

} catch (Exception e) {
    // e.printStackTrace(); // 上線請關閉
}

out.println("{\"success\":" + success + "}");
%>

<%!
public Boolean valid(String loginName, String token, HttpSession session) {
    try {
        // ===== 1. 取得 UUID =====
        URL url = new URL("https://sso.water.gov.tw/app_user/get_node_uuid/");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();

        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json");

        String body = "{"
            + "\"PRIVILEGED_APP_SSO_TOKEN\":\"你的SSO系統Token\","
            + "\"PUBLIC_APP_USER_SSO_TOKEN_TO_QUERY\":\"" + token + "\""
            + "}";

        conn.getOutputStream().write(body.getBytes("UTF-8"));

        BufferedReader br = new BufferedReader(
            new InputStreamReader(conn.getInputStream(), "UTF-8")
        );

        StringBuilder res = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) res.append(line);

        JSONObject r = new JSONObject(res.toString());

        if (!"0".equals(r.getString("ERROR_CODE"))) return false;

        String companyUuid = r.getString("APP_COMPANY_UUID");
        String userUuid = r.getString("APP_USER_NODE_UUID");

        // ===== 2. 查 user =====
        URL url2 = new URL("https://sso.water.gov.tw/org_tree_surrogate/get_user_node/");
        HttpURLConnection conn2 = (HttpURLConnection) url2.openConnection();

        conn2.setRequestMethod("POST");
        conn2.setDoOutput(true);
        conn2.setRequestProperty("Content-Type", "application/json");

        String body2 = "{"
            + "\"PRIVILEGED_APP_SSO_TOKEN\":\"你的SSO系統Token\","
            + "\"PUBLIC_APP_USER_SSO_TOKEN\":\"" + token + "\","
            + "\"APP_COMPANY_UUID\":\"" + companyUuid + "\","
            + "\"APP_USER_NODE_UUID\":\"" + userUuid + "\""
            + "}";

        conn2.getOutputStream().write(body2.getBytes("UTF-8"));

        BufferedReader br2 = new BufferedReader(
            new InputStreamReader(conn2.getInputStream(), "UTF-8")
        );

        StringBuilder res2 = new StringBuilder();
        while ((line = br2.readLine()) != null) res2.append(line);

        JSONObject u = new JSONObject(res2.toString());

        if (!"0".equals(u.getString("ERROR_CODE"))) return false;

        JSONObject profile = u.getJSONObject("APP_USER_BASIC_PROFILE");

        // ===== 3. 狀態檢查 =====
        if (!"1".equals(profile.getString("APP_USER_STATUS"))) return false;

        // ===== 4. 建立 session =====
        session.setAttribute("loginUser", loginName);
        session.setAttribute("userUuid", userUuid);
        session.setAttribute("companyUuid", companyUuid);

        return true;

    } catch (Exception e) {
        return false;
    }
}
%>