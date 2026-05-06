package com.ai3.ecp.cus.chatmessagesummary.action;

import com.jeedsoft.quicksilver.base.action.EntityAction;
import com.jeedsoft.quicksilver.base.type.ActionContext;
import com.jeedsoft.quicksilver.base.type.DataResult;
import com.ai3.ecp.cus.chatmessagesummary.model.ChatMessageSummaryModel;

public interface ChatMessageSummaryAction extends EntityAction<ChatMessageSummaryModel>
{
	DataResult hello(ActionContext paramActionContext);
}
