package com.ai3.ecp.cus.chatmessagesummary.model;

import java.sql.ResultSet;

import org.json.JSONObject;

import com.jeedsoft.quicksilver.base.model.EntityModel;
import com.jeedsoft.common.advanced.db.dataset.Record;

public class ChatMessageSummaryModel extends EntityModel
{
	private static final long serialVersionUID = 1L;

	public ChatMessageSummaryModel()
	{
	}

	public ChatMessageSummaryModel(Record r)
	{
		super(r);
	}

	public ChatMessageSummaryModel(ResultSet rs)
	{
		super(rs);
	}

	public ChatMessageSummaryModel(JSONObject json)
	{
		super(json);
	}
}
