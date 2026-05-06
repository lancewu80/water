package com.ai3.ecp.cus.hrsync;

import java.util.UUID;

import com.ai3.ecp.cus.hrsync.dao.HrSyncDao;
import com.ai3.ecp.cus.hrsync.service.HrSyncService;
import com.jeedsoft.quicksilver.registry.Registry;

public class HrSyncHome
{
	public static final UUID UNIT_ID = UUID.fromString("4806684c-e000-3135-6003-1961e9cb6d01");
	public static final String CACHE_REGION = "cus_hrsync";

	public static HrSyncDao getDao()
	{
		return Registry.getDao(UNIT_ID);
	}

	public static HrSyncService getService()
	{
		return Registry.getService(UNIT_ID);
	}
}