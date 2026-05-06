package com.ai3.ecp.cus.chatmessagesummary;

import java.util.UUID;

import com.ai3.ecp.cus.chatmessagesummary.dao.ChatMessageSummaryDao;
import com.ai3.ecp.cus.chatmessagesummary.service.ChatMessageSummaryService;
import com.jeedsoft.quicksilver.registry.Registry;

public class ChatMessageSummaryHome
{
	public static final UUID UNIT_ID = UUID.fromString("4806684c-e000-3135-6003-1961e9cb6d00");
	public static final String CACHE_REGION = "cus_chatmessagesummary";

	public static ChatMessageSummaryDao getDao()
	{
		return Registry.getDao(UNIT_ID);
	}

	public static ChatMessageSummaryService getService()
	{
		return Registry.getService(UNIT_ID);
	}
}
