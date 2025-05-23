/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.apache.ranger.db;

import org.apache.ranger.common.db.BaseDao;
import org.apache.ranger.entity.XXPolicyExportAudit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Date;
import java.util.concurrent.TimeUnit;

@Service
public class XXPolicyExportAuditDao extends BaseDao<XXPolicyExportAudit> {
    private static final Logger logger = LoggerFactory.getLogger(XXPolicyExportAuditDao.class);

    public XXPolicyExportAuditDao(RangerDaoManagerBase daoManager) {
        super(daoManager);
    }

    public long deleteOlderThan(int olderThanInDays) {
        Date since = new Date(System.currentTimeMillis() - TimeUnit.DAYS.toMillis(olderThanInDays));

        logger.info("Deleting x_policy_export_audit records that are older than {} days, that is, older than {}", olderThanInDays, since);

        long ret = getEntityManager().createNamedQuery("XXPolicyExportAudit.deleteOlderThan").setParameter("olderThan", since).executeUpdate();

        logger.info("Deleted x_policy_export_audit {} records", ret);

        return ret;
    }
}
