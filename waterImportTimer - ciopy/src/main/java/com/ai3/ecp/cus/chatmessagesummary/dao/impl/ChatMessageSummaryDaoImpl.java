package com.ai3.ecp.cus.chatmessagesummary.dao.impl;

import com.jeedsoft.common.advanced.db.dataset.DataSet;
import com.jeedsoft.common.advanced.db.dataset.Record;
import com.jeedsoft.quicksilver.base.dao.impl.EntityDaoImpl;

import java.util.List;

import com.ai3.ecp.cus.chatmessagesummary.ChatMessageSummaryHome;
import com.ai3.ecp.cus.chatmessagesummary.dao.ChatMessageSummaryDao;
import com.ai3.ecp.cus.chatmessagesummary.model.ChatMessageSummaryModel;

public class ChatMessageSummaryDaoImpl extends EntityDaoImpl<ChatMessageSummaryModel> implements ChatMessageSummaryDao {
	public ChatMessageSummaryDaoImpl() {
		super(ChatMessageSummaryHome.UNIT_ID, ChatMessageSummaryModel.class);
	}

	@Override
	public DataSet<Record> getMessageFromRemoteDb(String targetDate) {
		return getExecutor("default").getDataSet(
				"""
						select TCM.FRoomId, TCSS.FChatId, TCSS.FContactId AS FUserId, TC.FName AS FUserName, TCSS.FAgentId, TU.FName AS FAgentName, TCM.FSenderId, TCMan.FName AS FSenderName, TCM.FSendTime, TCM.FContent, TCM.FType
						from TcChatMessage TCM
						left join TrChatSeatStatus TCSS on TCM.FRoomId = TCSS.FChatRoomId
						left join TsUser TU on TU.FId = TCSS.FAgentId
						left join TcContact TC on TC.FId = TCSS.FContactId
						left join TcChatMan TCMan on TCMan.FId = TCM.FSenderId
						where char(TCSS.FCreateTime, 1) = ?
						""",
				new Object[] { targetDate });
	}

	@Override
	public void insertChatMessageSummary(List<Object[]> argsList) {
		getExecutor().executeBatch(
				"insert into TpCUSmChatMessageSummary (FId, U_AgentId, U_AgentName, U_ChatId, U_Content, U_RoomId, U_SenderId, U_SenderName, U_SendTime, U_Type, U_UserId, U_UserName) VALUES ( ?,?,?,?,?,?,?,?,?,?,?,? )",
				argsList);
	}
}
