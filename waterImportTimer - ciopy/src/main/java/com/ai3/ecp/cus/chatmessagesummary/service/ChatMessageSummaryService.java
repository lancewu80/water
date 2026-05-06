package com.ai3.ecp.cus.chatmessagesummary.service;

import com.jeedsoft.quicksilver.base.service.EntityService;
import com.jeedsoft.quicksilver.base.type.ServiceContext;

import org.json.JSONObject;

import com.ai3.ecp.cus.chatmessagesummary.model.ChatMessageSummaryModel;

public interface ChatMessageSummaryService extends EntityService<ChatMessageSummaryModel>
{

	void getChatMessageSummary(ServiceContext sc, JSONObject args);
}
