package com.ai3.ecp.cus.hrsync;

import java.io.InputStream;
import java.util.Properties;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.ai3.ecp.cus.hrsync.dao.HrSyncDao;
import com.ai3.ecp.cus.hrsync.service.HrSyncService;
import com.jeedsoft.quicksilver.registry.Registry;

public class HrSyncHome
{
	private static final Logger logger = LoggerFactory.getLogger(HrSyncHome.class);

	public static final UUID UNIT_ID = UUID.fromString("4806684c-e000-3135-6003-1961e9cb6d01");
	public static final String CACHE_REGION = "cus_hrsync";

	public static final UUID DEFAULT_IDENTITY_TYPE_ID;
	public static final String DEFAULT_ACCOUNT_PASSWORD;
	public static final UUID DEPT_ROOT_FID;

	static {
		Properties props = new Properties();
		try (InputStream is = HrSyncHome.class.getClassLoader().getResourceAsStream("hrsync.properties")) {
			if (is != null) {
				props.load(is);
			}
		} catch (Exception e) {
			logger.warn("[HrSyncHome] 無法載入 hrsync.properties，使用預設值: {}", e.getMessage());
		}
		DEFAULT_IDENTITY_TYPE_ID = UUID.fromString(
				props.getProperty("hrsync.accountIdentityTypeId", "564cf69e-76d6-4baf-b584-6e04c2911dae"));
		DEFAULT_ACCOUNT_PASSWORD =
				props.getProperty("hrsync.accountDefaultPassword", "loclmjbekjjpejbkllnpebakjcgaifekgniemamkggajjbmmgdnhfgmfnchakhgnaflbahapbfokenfd");
		DEPT_ROOT_FID = UUID.fromString(
				props.getProperty("hrsync.TsDepartmentRootFId", "00000000-0000-0000-1001-000000000001"));
	}

	public static HrSyncDao getDao()
	{
		return Registry.getDao(UNIT_ID);
	}

	public static HrSyncService getService()
	{
		return Registry.getService(UNIT_ID);
	}
}