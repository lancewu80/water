package com.ai3.ecp.cus.chatmessagesummary.service.impl;

import com.jeedsoft.common.advanced.db.dataset.DataSet;
import com.jeedsoft.common.advanced.db.dataset.Record;
import com.jeedsoft.common.basic.util.JsonUtil;
import com.jeedsoft.quicksilver.base.service.impl.EntityServiceImpl;
import com.jeedsoft.quicksilver.base.type.ServiceContext;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.UUID;

import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.ai3.ecp.cus.chatmessagesummary.ChatMessageSummaryHome;
import com.ai3.ecp.cus.chatmessagesummary.service.ChatMessageSummaryService;
import com.ai3.ecp.cus.chatmessagesummary.model.ChatMessageSummaryModel;

public class ChatMessageSummaryServiceImpl extends EntityServiceImpl<ChatMessageSummaryModel> implements ChatMessageSummaryService
{
	private static final Logger logger = LoggerFactory.getLogger(ChatMessageSummaryServiceImpl.class);
	
	public ChatMessageSummaryServiceImpl()
	{
		super(ChatMessageSummaryHome.UNIT_ID, ChatMessageSummaryModel.class);
	}

	@Override
	public void getChatMessageSummary(ServiceContext sc, JSONObject args) {
		logger.debug("[getChatMessageSummary] Start");
		Date serviceStartTime = new Date();
		
		// get targetdate
		String targetDate = JsonUtil.getString(args, "date");
		logger.debug("[getChatMessageSummary] targetDate = {}", targetDate);
		
		// get message list from remote datebase
		DataSet<Record> messageList;
		messageList = ChatMessageSummaryHome.getDao().getMessageFromRemoteDb(targetDate);
		int messageCount = messageList.size();
		logger.debug("[z] getMessageFromRemoteDb success, size: {}", messageCount);
		// (FId, U_AgentId, U_AgentName, U_ChatId, U_Content, U_RoomId, U_SenderId, U_SenderName, U_SendTime, U_Type, U_UserId, U_UserName)
		List<Object[]> argsList = new ArrayList<Object[]>();
		for (Record message : messageList) {
			List<Object> m = new ArrayList<Object>();
			m.add(UUID.randomUUID());
			m.add(message.getUuid("FAgentId"));
			m.add(message.getString("FAgentName"));
			m.add(message.getUuid("FChatId"));
			m.add(message.getString("FContent"));
			m.add(message.getUuid("FRoomId"));
			m.add(message.getUuid("FSenderId"));
			m.add(message.getString("FSenderName"));
			m.add(message.getDate("FSendTime"));
			m.add(message.getString("FType"));
			m.add(message.getUuid("FUserId"));
			m.add(message.getString("FUserName"));
			
			argsList.add(m.toArray());
		}
		
		if(argsList.size() > 0) {
			ChatMessageSummaryHome.getDao().insertChatMessageSummary(argsList);
		}
		
		Date serviceEndTime = new Date();
		long l = serviceEndTime.getTime() - serviceStartTime.getTime();
		logger.debug("[getChatMessageSummary] Finish, importCount: {}, processTime: {}", argsList.size(), String.valueOf(l / 1000L) + "(s)");
	}
}
