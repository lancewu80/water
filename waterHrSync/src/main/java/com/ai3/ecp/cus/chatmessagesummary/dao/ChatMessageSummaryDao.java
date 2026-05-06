package com.ai3.ecp.cus.chatmessagesummary.dao;

import com.jeedsoft.common.advanced.db.dataset.DataSet;
import com.jeedsoft.common.advanced.db.dataset.Record;
import com.jeedsoft.quicksilver.base.dao.EntityDao;

import java.util.List;

import com.ai3.ecp.cus.chatmessagesummary.model.ChatMessageSummaryModel;

public interface ChatMessageSummaryDao extends EntityDao<ChatMessageSummaryModel>
{

	DataSet<Record> getMessageFromRemoteDb(String targetDate);

	void insertChatMessageSummary(List<Object[]> argsList);
}
