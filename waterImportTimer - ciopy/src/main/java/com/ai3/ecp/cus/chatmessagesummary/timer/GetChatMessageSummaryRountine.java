package com.ai3.ecp.cus.chatmessagesummary.timer;

import java.text.ParseException;
import java.util.Calendar;
import java.util.Date;
import java.util.UUID;

import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.text.SimpleDateFormat;
import java.text.DateFormat;

import com.ai3.ecp.cus.chatmessagesummary.ChatMessageSummaryHome;
import com.chainsea.ecp.common.util.DateUtil;
import com.jeedsoft.common.basic.util.JsonUtil;
import com.jeedsoft.quicksilver.base.type.ServiceContext;
import com.jeedsoft.quicksilver.timer.type.TimerRoutine;

public class GetChatMessageSummaryRountine implements TimerRoutine {
	private static final Logger logger = LoggerFactory.getLogger(GetChatMessageSummaryRountine.class);
	private String targetDate;

	public GetChatMessageSummaryRountine(JSONObject args) throws ParseException {
		Date td = JsonUtil.getDate(args, "targetDate", getDefaultTargetDate());
		DateFormat formater = new SimpleDateFormat("yyyy-MM-dd");
		this.targetDate = formater.format(td);
	}

	public GetChatMessageSummaryRountine() throws ParseException {
		Date td = getDefaultTargetDate();
		DateFormat formater = new SimpleDateFormat("yyyy-MM-dd");
		this.targetDate = formater.format(td);
	}

	private Date getDefaultTargetDate() {
		Date st = DateUtil.getCurrentDate();
		Calendar val = DateUtil.getCalendar(st);
		val.add(Calendar.DATE, -1);
		return val.getTime();
	}

	@Override
	public void execute() {
		logger.debug("[GetChatMessageSummaryRountine] start");
		ServiceContext sc = new ServiceContext(UUID.fromString("00000000-0000-0000-1002-000000000001"), "zh-tw");
		ChatMessageSummaryHome.getService().getChatMessageSummary(sc, (new JSONObject()).put("date", this.targetDate));
	}
}
