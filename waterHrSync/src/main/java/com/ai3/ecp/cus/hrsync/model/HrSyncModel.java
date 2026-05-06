package com.ai3.ecp.cus.hrsync.model;

import java.sql.ResultSet;

import org.json.JSONObject;

import com.jeedsoft.quicksilver.base.model.EntityModel;
import com.jeedsoft.common.advanced.db.dataset.Record;

public class HrSyncModel extends EntityModel
{
	private static final long serialVersionUID = 1L;

	public HrSyncModel()
	{
	}

	public HrSyncModel(Record r)
	{
		super(r);
	}

	public HrSyncModel(ResultSet rs)
	{
		super(rs);
	}

	public HrSyncModel(JSONObject json)
	{
		super(json);
	}
}