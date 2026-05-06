package com.ai3.ecp.cus.chatmessagesummary.api.impl;

import com.jeedsoft.quicksilver.base.api.impl.EntityApiImpl;
import com.jeedsoft.quicksilver.base.type.ApiContext;
import com.jeedsoft.quicksilver.base.type.JsonResult;
import com.jeedsoft.quicksilver.integration.annotation.Api;
import com.ai3.ecp.cus.chatmessagesummary.ChatMessageSummaryHome;
import com.ai3.ecp.cus.chatmessagesummary.api.ChatMessageSummaryApi;
import com.ai3.ecp.cus.chatmessagesummary.model.ChatMessageSummaryModel;

public class ChatMessageSummaryApiImpl extends EntityApiImpl<ChatMessageSummaryModel> implements ChatMessageSummaryApi {
	public ChatMessageSummaryApiImpl() {
		super(ChatMessageSummaryHome.UNIT_ID, ChatMessageSummaryModel.class);
	}

	@Override
	@Api(path = "/javalesson/hello", isTokenRequired = false, output = {}, input = {})
	public JsonResult hello(ApiContext context) {
		JsonResult result = new JsonResult();
		result.put("hello", "world");
		return result;
	}
}
