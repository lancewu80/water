package com.ai3.cus.ecpsso;

import java.util.UUID;

import com.ai3.cus.ecpsso.dao.SSOLoginLogDao;
import com.ai3.cus.ecpsso.service.SSOLoginLogService;

public class SSOLoginLogHome
{
	public static final UUID UNIT_ID = UUID.fromString("df6c8bac-d9ce-4e6c-c404-18fc8f33cec0");
	public static final String CACHE_REGION = "cus_ssologinlog";
	
	private static SSOLoginLogDao dao;
	private static SSOLoginLogService service;
	
	public static SSOLoginLogDao getDao()
	{
		return dao;
	}

	public static void setDao(SSOLoginLogDao dao)
	{
		SSOLoginLogHome.dao = dao;
	}
	
	public static SSOLoginLogService getService()
	{
		return service;
	}

	public static void setService(SSOLoginLogService service)
	{
		SSOLoginLogHome.service = service;
	}
}
