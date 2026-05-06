package com.ai3.ecp.cus.hrsync.timer;

import java.util.UUID;

import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.ai3.ecp.cus.hrsync.HrSyncHome;
import com.jeedsoft.quicksilver.base.type.ServiceContext;
import com.jeedsoft.quicksilver.timer.type.TimerRoutine;

/**
 * Timer routine for HR system synchronisation.
 * Scheduled to run daily at 02:00 (before the 04:00 database backup window).
 *
 * Sync logic:
 *  1. Read 總處 personnel from HR view (v_KM_USER, DEPARTMENTID starts with '00').
 *  2. Ensure department '總處' exists in ECP (TsDepartment).
 *  3. Create / update / disable ECP users (TsUser) and accounts (TsAccount).
 *  4. Assign default role; additionally assign sysAdmin role for IT personnel.
 *  5. Write result log: execution time, function name, total / success / fail counts.
 */
public class SyncHrDataRountine implements TimerRoutine
{
	private static final Logger logger = LoggerFactory.getLogger(SyncHrDataRountine.class);

	public SyncHrDataRountine(JSONObject args)
	{
	}

	public SyncHrDataRountine()
	{
	}

	@Override
	public void execute()
	{
		logger.debug("[SyncHrDataRountine] start");
		ServiceContext sc = new ServiceContext(UUID.fromString("00000000-0000-0000-1002-000000000001"), "zh-tw");
		HrSyncHome.getService().syncHrData(sc);
	}
}