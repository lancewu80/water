package com.ai3.ecp.cus.hrsync.service;

import com.jeedsoft.quicksilver.base.service.EntityService;
import com.jeedsoft.quicksilver.base.type.ServiceContext;

import com.ai3.ecp.cus.hrsync.model.HrSyncModel;

public interface HrSyncService extends EntityService<HrSyncModel>
{
	void syncHrData(ServiceContext sc);
}