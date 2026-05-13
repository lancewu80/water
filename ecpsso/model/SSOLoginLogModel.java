package com.ai3.cus.ecpsso.model;

import java.sql.ResultSet;

import org.json.JSONObject;

import com.jeedsoft.quicksilver.base.model.EntityModel;
import com.jeedsoft.common.advanced.db.dataset.Record;

public class SSOLoginLogModel extends EntityModel
{
	private static final long serialVersionUID = 1L;

	public SSOLoginLogModel()
	{
	}

	public SSOLoginLogModel(Record r)
	{
		super(r);
	}

	public SSOLoginLogModel(ResultSet rs)
	{
		super(rs);
	}

	public SSOLoginLogModel(JSONObject json)
	{
		super(json);
	}
}
