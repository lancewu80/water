package com.ai3.ecp.cus.chatmessagesummary.api;

import com.jeedsoft.quicksilver.base.api.EntityApi;
import com.jeedsoft.quicksilver.base.type.ApiContext;
import com.jeedsoft.quicksilver.base.type.JsonResult;
import com.ai3.ecp.cus.chatmessagesummary.model.ChatMessageSummaryModel;

public interface ChatMessageSummaryApi extends EntityApi<ChatMessageSummaryModel>
{
	JsonResult hello(ApiContext context);
}
