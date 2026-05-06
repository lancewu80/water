package com.ai3.ecp.cus.chatmessagesummary.action.impl;

import com.jeedsoft.quicksilver.base.action.impl.EntityActionImpl;
import com.jeedsoft.quicksilver.base.type.ActionContext;
import com.jeedsoft.quicksilver.base.type.DataResult;
import com.ai3.ecp.cus.chatmessagesummary.ChatMessageSummaryHome;
import com.ai3.ecp.cus.chatmessagesummary.action.ChatMessageSummaryAction;
import com.ai3.ecp.cus.chatmessagesummary.model.ChatMessageSummaryModel;

public class ChatMessageSummaryActionImpl extends EntityActionImpl<ChatMessageSummaryModel> implements ChatMessageSummaryAction
{
	public ChatMessageSummaryActionImpl()
	{
		super(ChatMessageSummaryHome.UNIT_ID, ChatMessageSummaryModel.class);
	}

	@Override
	public DataResult hello(ActionContext paramActionContext) {
		return (new DataResult()).put("hello", "world");
	}
}
