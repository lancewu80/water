<%@page import="org.json.*"%>
<%
    // 設定回傳格式(json，UTF-8)
	response.setContentType("application/json; charset=UTF-8");
    // 宣告變數以及賦予預設值
	boolean success = false;
    String loginName = "";
    String password = "";
    String content = "";

	try {
        // 從ECP傳入參數取得使用者登打的帳號密碼
		content = request.getReader().readLine();
		JSONObject json = new JSONObject(content);
		loginName = json.getString("loginName");
		password = json.getString("password");

        // 驗密邏輯，若驗密成功則success為true
		success = valid(loginName, password);
	}
	catch (Exception e) {
        // 測試期間可以看錯誤訊息，正式上線時要註解
		// out.println(e);
	}

    // 回傳結果給ECP，主要是要回傳success的值
    out.println("{\"success\":" + success + "}");
    // 測試期間，可以多回傳其他變數來除錯
    // out.println("{\"success\":" + success + ", \"loginName\":\"" + loginName + "\", \"password\":\"" + password + "\", \"content\":" + content + "}");
%>

<%! 
    /**
     * TODO: 驗密邏輯
     */
    public Boolean valid(String loginName, String password) {
		return password.equals("123123");
    }
%>
