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

package org.apache.ranger.biz;

import org.apache.commons.lang.StringUtils;
import org.apache.ranger.amazon.cloudwatch.CloudWatchAccessAuditsService;
import org.apache.ranger.authorization.hadoop.config.RangerAdminConfig;
import org.apache.ranger.common.AppConstants;
import org.apache.ranger.common.DateUtil;
import org.apache.ranger.common.JSONUtil;
import org.apache.ranger.common.MessageEnums;
import org.apache.ranger.common.RangerCommonEnums;
import org.apache.ranger.common.RangerConstants;
import org.apache.ranger.common.SearchCriteria;
import org.apache.ranger.common.StringUtil;
import org.apache.ranger.common.db.RangerTransactionSynchronizationAdapter;
import org.apache.ranger.db.RangerDaoManager;
import org.apache.ranger.elasticsearch.ElasticSearchAccessAuditsService;
import org.apache.ranger.entity.XXPermMap;
import org.apache.ranger.entity.XXPluginInfo;
import org.apache.ranger.entity.XXPolicyExportAudit;
import org.apache.ranger.entity.XXPortalUser;
import org.apache.ranger.entity.XXUser;
import org.apache.ranger.plugin.model.RangerPluginInfo;
import org.apache.ranger.plugin.store.PList;
import org.apache.ranger.plugin.util.RangerPluginCapability;
import org.apache.ranger.plugin.util.RangerRESTUtils;
import org.apache.ranger.plugin.util.SearchFilter;
import org.apache.ranger.service.RangerPluginInfoService;
import org.apache.ranger.service.RangerTrxLogV2Service;
import org.apache.ranger.service.XAccessAuditService;
import org.apache.ranger.service.XAuditMapService;
import org.apache.ranger.service.XGroupService;
import org.apache.ranger.service.XPermMapService;
import org.apache.ranger.service.XPolicyService;
import org.apache.ranger.service.XUgsyncAuditInfoService;
import org.apache.ranger.service.XUserService;
import org.apache.ranger.solr.SolrAccessAuditsService;
import org.apache.ranger.util.RestUtil;
import org.apache.ranger.view.VXAccessAuditList;
import org.apache.ranger.view.VXAsset;
import org.apache.ranger.view.VXAuditMap;
import org.apache.ranger.view.VXGroup;
import org.apache.ranger.view.VXGroupList;
import org.apache.ranger.view.VXPermMap;
import org.apache.ranger.view.VXPolicyExportAuditList;
import org.apache.ranger.view.VXResource;
import org.apache.ranger.view.VXTrxLog;
import org.apache.ranger.view.VXTrxLogList;
import org.apache.ranger.view.VXTrxLogV2;
import org.apache.ranger.view.VXTrxLogV2.AttributeChangeInfo;
import org.apache.ranger.view.VXTrxLogV2.ObjectChangeInfo;
import org.apache.ranger.view.VXTrxLogV2List;
import org.apache.ranger.view.VXUgsyncAuditInfoList;
import org.apache.ranger.view.VXUser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import javax.annotation.PostConstruct;
import javax.naming.InvalidNameException;
import javax.naming.ldap.LdapName;
import javax.naming.ldap.Rdn;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Component
public class AssetMgr extends AssetMgrBase {
    private static final Logger logger = LoggerFactory.getLogger(AssetMgr.class);

    private static final String PROP_RANGER_LOG_SC_NOT_MODIFIED          = "ranger.log.SC_NOT_MODIFIED";
    private static final String PROP_PLUGIN_ACTIVITY_AUDIT_NOT_MODIFIED  = "ranger.plugin.activity.audit.not.modified";
    private static final String PROP_PLUGIN_ACTIVITY_AUDIT_COMMIT_INLINE = "ranger.plugin.activity.audit.commit.inline";
    private static final String adminCapabilities = Long.toHexString(new RangerPluginCapability().getPluginCapabilities());

    @Autowired
    XPermMapService xPermMapService;

    @Autowired
    XAuditMapService xAuditMapService;

    @Autowired
    JSONUtil jsonUtil;

    @Autowired
    RangerBizUtil msBizUtil;

    @Autowired
    StringUtil stringUtil;

    @Autowired
    RangerDaoManager rangerDaoManager;

    @Autowired
    XUserService xUserService;

    @Autowired
    RangerBizUtil xaBizUtil;

    @Autowired
    RangerTrxLogV2Service xTrxLogService;

    @Autowired
    XAccessAuditService xAccessAuditService;

    @Autowired
    XGroupService xGroupService;

    @Autowired
    XUserMgr xUserMgr;

    @Autowired
    SolrAccessAuditsService solrAccessAuditsService;

    @Autowired
    ElasticSearchAccessAuditsService elasticSearchAccessAuditsService;

    @Autowired
    CloudWatchAccessAuditsService cloudWatchAccessAuditsService;

    @Autowired
    XPolicyService xPolicyService;

    @Autowired
    RangerTransactionSynchronizationAdapter transactionSynchronizationAdapter;

    @Autowired
    RangerPluginInfoService pluginInfoService;

    @Autowired
    XUgsyncAuditInfoService xUgsyncAuditInfoService;

    @Autowired
    ServiceMgr serviceMgr;

    boolean rangerLogNotModified;
    boolean pluginActivityAuditLogNotModified;
    boolean pluginActivityAuditCommitInline;

    @PostConstruct
    public void init() {
        logger.info("==> AssetMgr.init()");

        rangerLogNotModified              = RangerAdminConfig.getInstance().getBoolean(PROP_RANGER_LOG_SC_NOT_MODIFIED, false);
        pluginActivityAuditLogNotModified = RangerAdminConfig.getInstance().getBoolean(PROP_PLUGIN_ACTIVITY_AUDIT_NOT_MODIFIED, false);
        pluginActivityAuditCommitInline   = RangerAdminConfig.getInstance().getBoolean(PROP_PLUGIN_ACTIVITY_AUDIT_COMMIT_INLINE, false);

        logger.info("{}={}", PROP_RANGER_LOG_SC_NOT_MODIFIED, rangerLogNotModified);
        logger.info("{}={}", PROP_PLUGIN_ACTIVITY_AUDIT_NOT_MODIFIED, pluginActivityAuditLogNotModified);
        logger.info("{}={}", PROP_PLUGIN_ACTIVITY_AUDIT_COMMIT_INLINE, pluginActivityAuditCommitInline);

        logger.info("<== AssetMgr.init()");
    }

    public String getLatestRepoPolicy(VXAsset xAsset, List<VXResource> xResourceList, Long updatedTime, X509Certificate[] certchain, boolean httpEnabled, String epoch, String ipAddress, boolean isSecure, String count, String agentId) {
        if (xAsset == null) {
            logger.error("Requested repository not found");

            throw restErrorUtil.createRESTException("No Data Found.", MessageEnums.DATA_NOT_FOUND);
        }

        if (xResourceList == null) {
            logger.error("ResourceList is found");

            throw restErrorUtil.createRESTException("No Data Found.", MessageEnums.DATA_NOT_FOUND);
        }

        if (xAsset.getActiveStatus() == RangerCommonEnums.ACT_STATUS_DISABLED) {
            logger.error("Requested repository is disabled");

            throw restErrorUtil.createRESTException("Unauthorized access.", MessageEnums.OPER_NO_EXPORT);
        }

        HashMap<String, Object> updatedRepo = new HashMap<>();

        updatedRepo.put("repository_name", xAsset.getName());

        XXPolicyExportAudit policyExportAudit = new XXPolicyExportAudit();

        policyExportAudit.setRepositoryName(xAsset.getName());

        if (agentId != null && !agentId.isEmpty()) {
            policyExportAudit.setAgentId(agentId);
        }

        policyExportAudit.setClientIP(ipAddress);

        if (epoch != null && !epoch.trim().isEmpty() && !"null".equalsIgnoreCase(epoch)) {
            policyExportAudit.setRequestedEpoch(Long.parseLong(epoch));
        } else {
            policyExportAudit.setRequestedEpoch(0L);
        }

        if (!httpEnabled) {
            if (!isSecure) {
                policyExportAudit.setHttpRetCode(HttpServletResponse.SC_BAD_REQUEST);

                createPolicyAudit(policyExportAudit);

                throw restErrorUtil.createRESTException("Unauthorized access - only https allowed", MessageEnums.OPER_NOT_ALLOWED_FOR_ENTITY);
            }

            if (certchain == null || certchain.length == 0) {
                policyExportAudit.setHttpRetCode(HttpServletResponse.SC_BAD_REQUEST);

                createPolicyAudit(policyExportAudit);

                throw restErrorUtil.createRESTException("Unauthorized access - unable to get client certificate", MessageEnums.OPER_NOT_ALLOWED_FOR_ENTITY);
            }
        }

        Long   policyCount = restErrorUtil.parseLong(count, "Invalid value for policyCount", MessageEnums.INVALID_INPUT_DATA, null, "policyCount");
        String commonName  = null;

        if (certchain != null) {
            X509Certificate clientCert = certchain[0];
            String          dn         = clientCert.getSubjectX500Principal().getName();

            try {
                LdapName ln = new LdapName(dn);

                for (Rdn rdn : ln.getRdns()) {
                    if ("CN".equalsIgnoreCase(rdn.getType())) {
                        commonName = rdn.getValue() + "";
                        break;
                    }
                }

                if (commonName == null) {
                    policyExportAudit.setHttpRetCode(HttpServletResponse.SC_BAD_REQUEST);

                    createPolicyAudit(policyExportAudit);

                    throw restErrorUtil.createRESTException("Unauthorized access - Unable to find Common Name from [" + dn + "]", MessageEnums.OPER_NOT_ALLOWED_FOR_ENTITY);
                }
            } catch (InvalidNameException e) {
                policyExportAudit.setHttpRetCode(HttpServletResponse.SC_BAD_REQUEST);

                createPolicyAudit(policyExportAudit);

                logger.error("Invalid Common Name.", e);

                throw restErrorUtil.createRESTException("Unauthorized access - Invalid Common Name", MessageEnums.OPER_NOT_ALLOWED_FOR_ENTITY);
            }
        }

        if (policyCount == null) {
            policyCount = 0L;
        }

        if (commonName != null) {
            String              config       = xAsset.getConfig();
            Map<String, String> configMap    = jsonUtil.jsonToMap(config);
            String              cnFromConfig = configMap.get("commonNameForCertificate");

            if (!commonName.equalsIgnoreCase(cnFromConfig)) {
                policyExportAudit.setHttpRetCode(HttpServletResponse.SC_BAD_REQUEST);

                createPolicyAudit(policyExportAudit);

                throw restErrorUtil.createRESTException("Unauthorized access. expected [" + cnFromConfig + "], found [" + commonName + "]", MessageEnums.OPER_NOT_ALLOWED_FOR_ENTITY);
            }
        }

        long epochTime = epoch != null ? Long.parseLong(epoch) : 0;

        if (epochTime == updatedTime) {
            int resourceListSz = xResourceList.size();

            if (policyCount == resourceListSz) {
                policyExportAudit.setHttpRetCode(HttpServletResponse.SC_NOT_MODIFIED);

                createPolicyAudit(policyExportAudit);

                throw restErrorUtil.createRESTException(HttpServletResponse.SC_NOT_MODIFIED, "No change since last update", false);
            }
        }

        List<HashMap<String, Object>> resourceList = new ArrayList<>();

        // HDFS Repository
        if (xAsset.getAssetType() == AppConstants.ASSET_HDFS) {
            for (VXResource xResource : xResourceList) {
                HashMap<String, Object> resourceMap = new HashMap<>();

                resourceMap.put("id", xResource.getId());
                resourceMap.put("resource", xResource.getName());
                resourceMap.put("isRecursive", getBooleanValue(xResource.getIsRecursive()));
                resourceMap.put("policyStatus", RangerCommonEnums.getLabelFor_ActiveStatus(xResource.getResourceStatus()));
                // resourceMap.put("isEncrypt", AKAConstants.getLabelFor_BooleanValue(xResource.getIsEncrypt()));
                populatePermMap(xResource, resourceMap, AppConstants.ASSET_HDFS);

                List<VXAuditMap> xAuditMaps = xResource.getAuditList();

                if (!xAuditMaps.isEmpty()) {
                    resourceMap.put("audit", 1);
                } else {
                    resourceMap.put("audit", 0);
                }

                resourceList.add(resourceMap);
            }
        } else if (xAsset.getAssetType() == AppConstants.ASSET_HIVE) {
            for (VXResource xResource : xResourceList) {
                HashMap<String, Object> resourceMap = new HashMap<>();

                resourceMap.put("id", xResource.getId());
                resourceMap.put("database_name", xResource.getDatabases());
                resourceMap.put("policyStatus", RangerCommonEnums.getLabelFor_ActiveStatus(xResource.getResourceStatus()));
                resourceMap.put("tablePolicyType", AppConstants.getLabelFor_PolicyType(xResource.getTableType()));
                resourceMap.put("columnPolicyType", AppConstants.getLabelFor_PolicyType(xResource.getColumnType()));

                int resourceType = xResource.getResourceType();

                if (resourceType == AppConstants.RESOURCE_UDF) {
                    resourceMap.put("udf_name", xResource.getUdfs());
                } else if (resourceType == AppConstants.RESOURCE_COLUMN) {
                    resourceMap.put("table_name", xResource.getTables());
                    resourceMap.put("column_name", xResource.getColumns());
                } else if (resourceType == AppConstants.RESOURCE_TABLE) {
                    resourceMap.put("table_name", xResource.getTables());
                }

                populatePermMap(xResource, resourceMap, AppConstants.ASSET_HIVE);

                List<VXAuditMap> xAuditMaps = xResource.getAuditList();

                if (!xAuditMaps.isEmpty()) {
                    resourceMap.put("audit", 1);
                } else {
                    resourceMap.put("audit", 0);
                }

                resourceList.add(resourceMap);
            }
        } else if (xAsset.getAssetType() == AppConstants.ASSET_HBASE) {
            for (VXResource xResource : xResourceList) {
                HashMap<String, Object> resourceMap = new HashMap<>();

                resourceMap.put("id", xResource.getId());
                resourceMap.put("table_name", xResource.getTables());
                resourceMap.put("column_name", xResource.getColumns());
                resourceMap.put("column_families", xResource.getColumnFamilies());
                resourceMap.put("policyStatus", RangerCommonEnums.getLabelFor_ActiveStatus(xResource.getResourceStatus()));

                if (xResource.getIsEncrypt() == 1) {
                    resourceMap.put("encrypt", 1);
                } else {
                    resourceMap.put("encrypt", 0);
                }

                // resourceMap.put("isEncrypt", AKAConstants.getLabelFor_BooleanValue(xResource.getIsEncrypt()));
                populatePermMap(xResource, resourceMap, AppConstants.ASSET_HBASE);

                List<VXAuditMap> xAuditMaps = xResource.getAuditList();

                if (!xAuditMaps.isEmpty()) {
                    resourceMap.put("audit", 1);
                } else {
                    resourceMap.put("audit", 0);
                }

                resourceList.add(resourceMap);
            }
        } else if (xAsset.getAssetType() == AppConstants.ASSET_KNOX) {
            for (VXResource xResource : xResourceList) {
                HashMap<String, Object> resourceMap = new HashMap<>();

                resourceMap.put("id", xResource.getId());
                resourceMap.put("topology_name", xResource.getTopologies());
                resourceMap.put("service_name", xResource.getServices());
                resourceMap.put("policyStatus", RangerCommonEnums.getLabelFor_ActiveStatus(xResource.getResourceStatus()));

                if (xResource.getIsEncrypt() == 1) {
                    resourceMap.put("encrypt", 1);
                } else {
                    resourceMap.put("encrypt", 0);
                }

                // resourceMap.put("isEncrypt", AKAConstants.getLabelFor_BooleanValue(xResource.getIsEncrypt()));
                populatePermMap(xResource, resourceMap, AppConstants.ASSET_KNOX);

                List<VXAuditMap> xAuditMaps = xResource.getAuditList();

                if (!xAuditMaps.isEmpty()) {
                    resourceMap.put("audit", 1);
                } else {
                    resourceMap.put("audit", 0);
                }

                resourceList.add(resourceMap);
            }
        } else if (xAsset.getAssetType() == AppConstants.ASSET_STORM) {
            for (VXResource xResource : xResourceList) {
                HashMap<String, Object> resourceMap = new HashMap<>();

                resourceMap.put("id", xResource.getId());
                resourceMap.put("topology_name", xResource.getTopologies());
                resourceMap.put("policyStatus", RangerCommonEnums.getLabelFor_ActiveStatus(xResource.getResourceStatus()));

                if (xResource.getIsEncrypt() == 1) {
                    resourceMap.put("encrypt", 1);
                } else {
                    resourceMap.put("encrypt", 0);
                }

                populatePermMap(xResource, resourceMap, AppConstants.ASSET_STORM);

                List<VXAuditMap> xAuditMaps = xResource.getAuditList();

                if (!xAuditMaps.isEmpty()) {
                    resourceMap.put("audit", 1);
                } else {
                    resourceMap.put("audit", 0);
                }

                resourceList.add(resourceMap);
            }
        } else {
            policyExportAudit.setHttpRetCode(HttpServletResponse.SC_BAD_REQUEST);

            createPolicyAudit(policyExportAudit);

            throw restErrorUtil.createRESTException("The operation isn't yet supported for the repository", MessageEnums.OPER_NOT_ALLOWED_FOR_ENTITY);
        }

        policyCount = (long) resourceList.size();

        updatedRepo.put("last_updated", updatedTime);
        updatedRepo.put("policyCount", policyCount);
        updatedRepo.put("acl", resourceList);

        String updatedPolicyStr = jsonUtil.readMapToString(updatedRepo);

        // File file = null;
        // try {
        //     file = jsonUtil.writeMapToFile(updatedRepo, repository);
        // } catch (JsonGenerationException e) {
        //     logger.error("Error exporting policies for repository : {}", repository, e);
        // } catch (JsonMappingException e) {
        //     logger.error("Error exporting policies for repository : {}", repository, e);
        // } catch (IOException e) {
        //     logger.error("Error exporting policies for repository : {}", repository, e);
        // }

        policyExportAudit.setHttpRetCode(HttpServletResponse.SC_OK);

        createPolicyAudit(policyExportAudit);

        return updatedPolicyStr;
    }

    public void updateDefaultPolicyUserAndPerm(VXResource vXResource, String userName) {
        if (userName != null && !userName.isEmpty()) {
            XXUser xxUser = rangerDaoManager.getXXUser().findByUserName(userName);
            VXUser vXUser;

            if (xxUser != null) {
                vXUser = xUserService.populateViewBean(xxUser);
            } else {
                vXUser = new VXUser();

                vXUser.setName(userName);
                // FIXME hack : unnecessary.
                vXUser.setDescription(userName);

                vXUser = xUserService.createResource(vXUser);
            }

            // fetch old permission and consider only one permission for default policy
            List<XXPermMap> xxPermMapList = rangerDaoManager.getXXPermMap().findByResourceId(vXResource.getId());
            VXPermMap       vXPermMap     = null;

            if (xxPermMapList != null && !xxPermMapList.isEmpty()) {
                vXPermMap = xPermMapService.populateViewBean(xxPermMapList.get(0));
            }

            if (vXPermMap == null) {
                // create new permission
                vXPermMap = new VXPermMap();

                vXPermMap.setUserId(vXUser.getId());
                vXPermMap.setResourceId(vXResource.getId());
            } else {
                // update old permission after updating userid
                vXPermMap.setUserId(vXUser.getId());

                xPermMapService.updateResource(vXPermMap);
            }
        }
    }

    public void createPolicyAudit(final XXPolicyExportAudit xXPolicyExportAudit) {
        final Runnable commitWork;

        if (xXPolicyExportAudit.getHttpRetCode() == HttpServletResponse.SC_NOT_MODIFIED) {
            if (!rangerLogNotModified) {
                logger.debug("Not logging HttpServletResponse. SC_NOT_MODIFIED. To enable, set configuration: {}=true", PROP_RANGER_LOG_SC_NOT_MODIFIED);

                commitWork = null;
            } else {
                // Create PolicyExportAudit record after transaction is completed. If it is created in-line here
                // then the TransactionManager will roll-back the changes because the HTTP return code is
                // HttpServletResponse.SC_NOT_MODIFIED
                commitWork = () -> rangerDaoManager.getXXPolicyExportAudit().create(xXPolicyExportAudit);
            }
        } else {
            commitWork = () -> rangerDaoManager.getXXPolicyExportAudit().create(xXPolicyExportAudit);
        }

        if (commitWork != null) {
            if (pluginActivityAuditCommitInline) {
                transactionSynchronizationAdapter.executeOnTransactionCompletion(commitWork);
            } else {
                transactionSynchronizationAdapter.executeAsyncOnTransactionComplete(commitWork);
            }
        }
    }

    public void createPluginInfo(String serviceName, String pluginId, HttpServletRequest request, int entityType, Long downloadedVersion, Long lastKnownVersion, long lastActivationTime, int httpCode, String clusterName, String pluginCapabilities) {
        RangerRESTUtils restUtils   = new RangerRESTUtils();
        final String    ipAddress   = getRemoteAddress(request);
        final String    appType     = restUtils.getAppIdFromPluginId(pluginId);
        String          tmpHostName = null;

        if (StringUtils.isNotBlank(pluginId)) {
            tmpHostName = restUtils.getHostnameFromPluginId(pluginId, serviceName);
        }

        if (StringUtils.isBlank(tmpHostName) && request != null) {
            tmpHostName = request.getRemoteHost();
        }

        final String hostName = (StringUtils.isBlank(tmpHostName)) ? ipAddress : tmpHostName;

        RangerPluginInfo pluginSvcVersionInfo = new RangerPluginInfo();

        pluginSvcVersionInfo.setServiceName(serviceName);
        pluginSvcVersionInfo.setAppType(appType);
        pluginSvcVersionInfo.setHostName(hostName);
        pluginSvcVersionInfo.setIpAddress(ipAddress);
        pluginSvcVersionInfo.setPluginCapabilities(StringUtils.isEmpty(pluginCapabilities) ? RangerPluginCapability.getBaseRangerCapabilities() : pluginCapabilities);

        switch (entityType) {
            case RangerPluginInfo.ENTITY_TYPE_POLICIES:
                pluginSvcVersionInfo.setPolicyActiveVersion(lastKnownVersion);
                pluginSvcVersionInfo.setPolicyActivationTime(lastActivationTime);
                pluginSvcVersionInfo.setPolicyDownloadedVersion(downloadedVersion);
                pluginSvcVersionInfo.setPolicyDownloadTime(new Date().getTime());
                break;
            case RangerPluginInfo.ENTITY_TYPE_TAGS:
                pluginSvcVersionInfo.setTagActiveVersion(lastKnownVersion);
                pluginSvcVersionInfo.setTagActivationTime(lastActivationTime);
                pluginSvcVersionInfo.setTagDownloadedVersion(downloadedVersion);
                pluginSvcVersionInfo.setTagDownloadTime(new Date().getTime());
                break;
            case RangerPluginInfo.ENTITY_TYPE_ROLES:
                pluginSvcVersionInfo.setRoleActiveVersion(lastKnownVersion);
                pluginSvcVersionInfo.setRoleActivationTime(lastActivationTime);
                pluginSvcVersionInfo.setRoleDownloadedVersion(downloadedVersion);
                pluginSvcVersionInfo.setRoleDownloadTime(new Date().getTime());
                break;
            case RangerPluginInfo.ENTITY_TYPE_USERSTORE:
                pluginSvcVersionInfo.setUserStoreActiveVersion(lastKnownVersion);
                pluginSvcVersionInfo.setUserStoreActivationTime(lastActivationTime);
                pluginSvcVersionInfo.setUserStoreDownloadedVersion(downloadedVersion);
                pluginSvcVersionInfo.setUserStoreDownloadTime(new Date().getTime());
                break;
            case RangerPluginInfo.ENTITY_TYPE_GDS:
                pluginSvcVersionInfo.setGdsActiveVersion(lastKnownVersion);
                pluginSvcVersionInfo.setGdsActivationTime(lastActivationTime);
                pluginSvcVersionInfo.setGdsDownloadedVersion(downloadedVersion);
                pluginSvcVersionInfo.setGdsDownloadTime(new Date().getTime());
                break;
        }

        createOrUpdatePluginInfo(pluginSvcVersionInfo, entityType, httpCode, clusterName);
    }

    public VXTrxLogList getReportLogs(SearchCriteria searchCriteria) {
        VXTrxLogList      ret;
        PList<VXTrxLogV2> vXTrxLogsV2 = getVXTrxLogsV2(searchCriteria);
        List<VXTrxLog>    vxTrxLogs   = vXTrxLogsV2.getList().stream().map(VXTrxLogV2::toVXTrxLog).collect(Collectors.toList());

        if (CollectionUtils.isEmpty(vxTrxLogs)) {
            ret = new VXTrxLogList(Collections.emptyList());
        } else {
            ret = new VXTrxLogList(validateXXTrxLogList(vxTrxLogs));

            ret.setStartIndex(vXTrxLogsV2.getStartIndex());
            ret.setPageSize(vXTrxLogsV2.getPageSize());
            ret.setTotalCount(vXTrxLogsV2.getTotalCount());
            ret.setResultSize(vXTrxLogsV2.getResultSize());
            ret.setSortBy(vXTrxLogsV2.getSortBy());
            ret.setSortType(vXTrxLogsV2.getSortType());
        }

        return ret;
    }

    public VXTrxLogV2List getReportLogsV2(SearchCriteria searchCriteria) {
        VXTrxLogV2List    ret;
        PList<VXTrxLogV2> vXTrxLogsV2 = getVXTrxLogsV2(searchCriteria);

        if (vXTrxLogsV2 == null || CollectionUtils.isEmpty(vXTrxLogsV2.getList())) {
            ret = new VXTrxLogV2List(Collections.emptyList());
        } else {
            ret = new VXTrxLogV2List(validateXXTrxLogV2List(vXTrxLogsV2.getList()));

            ret.setStartIndex(vXTrxLogsV2.getStartIndex());
            ret.setPageSize(vXTrxLogsV2.getPageSize());
            ret.setTotalCount(vXTrxLogsV2.getTotalCount());
            ret.setResultSize(vXTrxLogsV2.getResultSize());
            ret.setSortBy(vXTrxLogsV2.getSortBy());
            ret.setSortType(vXTrxLogsV2.getSortType());
        }
        return ret;
    }

    public PList<VXTrxLogV2> getVXTrxLogsV2(SearchCriteria searchCriteria) {
        if (xaBizUtil.isAdmin() || xaBizUtil.isKeyAdmin() || xaBizUtil.isAuditAdmin() || xaBizUtil.isAuditKeyAdmin()) {
            if (searchCriteria == null) {
                searchCriteria = new SearchCriteria();
            }

            if (searchCriteria.getParamList() != null && !searchCriteria.getParamList().isEmpty()) {
                int      clientTimeOffsetInMinute = RestUtil.getClientTimeOffset();
                DateUtil dateUtil                 = new DateUtil();

                if (searchCriteria.getParamList().containsKey("startDate")) {
                    Date temp = (Date) searchCriteria.getParamList().get("startDate");

                    temp = dateUtil.getDateFromGivenDate(temp, 0, 0, 0, 0);
                    temp = dateUtil.addTimeOffset(temp, clientTimeOffsetInMinute);

                    searchCriteria.getParamList().put("startDate", temp);
                }

                if (searchCriteria.getParamList().containsKey("endDate")) {
                    Date temp = (Date) searchCriteria.getParamList().get("endDate");

                    temp = dateUtil.getDateFromGivenDate(temp, 0, 23, 59, 59);
                    temp = dateUtil.addTimeOffset(temp, clientTimeOffsetInMinute);

                    searchCriteria.getParamList().put("endDate", temp);
                }

                if (searchCriteria.getParamList().containsKey("owner")) {
                    XXPortalUser xXPortalUser = rangerDaoManager.getXXPortalUser().findByLoginId((searchCriteria.getParamList().get("owner").toString()));

                    if (xXPortalUser != null) {
                        searchCriteria.getParamList().put("owner", xXPortalUser.getId());
                    } else {
                        searchCriteria.getParamList().put("owner", 0);
                    }
                }
            }

            searchCriteria.setGetCount(true);

            return xTrxLogService.searchTrxLogs(searchCriteria);
        } else {
            throw restErrorUtil.create403RESTException("Permission Denied !");
        }
    }

    public VXAccessAuditList getAccessLogs(SearchCriteria searchCriteria) {
        if (searchCriteria == null) {
            searchCriteria = new SearchCriteria();
        }

        if (searchCriteria.getParamList() != null && !searchCriteria.getParamList().isEmpty()) {
            int      clientTimeOffsetInMinute = RestUtil.getClientTimeOffset();
            DateUtil dateUtil                 = new DateUtil();

            if (searchCriteria.getParamList().containsKey("startDate")) {
                Date temp = (Date) searchCriteria.getParamList().get("startDate");

                temp = dateUtil.getDateFromGivenDate(temp, 0, 0, 0, 0);
                temp = dateUtil.addTimeOffset(temp, clientTimeOffsetInMinute);

                searchCriteria.getParamList().put("startDate", temp);
            }

            if (searchCriteria.getParamList().containsKey("endDate")) {
                Date temp = (Date) searchCriteria.getParamList().get("endDate");

                temp = dateUtil.getDateFromGivenDate(temp, 0, 23, 59, 59);
                temp = dateUtil.addTimeOffset(temp, clientTimeOffsetInMinute);

                searchCriteria.getParamList().put("endDate", temp);
            }
        }

        if (searchCriteria.getSortType() == null) {
            searchCriteria.setSortType("desc");
        } else if (!"asc".equalsIgnoreCase(searchCriteria.getSortType()) && !"desc".equalsIgnoreCase(searchCriteria.getSortType())) {
            searchCriteria.setSortType("desc");
        }

        if (!xaBizUtil.isAdmin()) {
            Long         userId      = xaBizUtil.getXUserId();
            List<String> userZones   = rangerDaoManager.getXXSecurityZoneDao().findZoneNamesByUserId(userId);
            Set<String>  zoneNameSet = new HashSet<>(userZones);
            VXGroupList  groupList   = xUserMgr.getXUserGroups(userId);

            for (VXGroup group : groupList.getList()) {
                List<String> userGroupZones = rangerDaoManager.getXXSecurityZoneDao().findZoneNamesByGroupId(group.getId());

                zoneNameSet.addAll(userGroupZones);
            }

            List<String> zoneNameList = (List<String>) searchCriteria.getParamValue("zoneName");

            if ((zoneNameList == null || zoneNameList.isEmpty())) {
                if (!zoneNameSet.isEmpty()) {
                    searchCriteria.getParamList().put("zoneName", new ArrayList<>(zoneNameSet));
                } else {
                    searchCriteria.getParamList().put("zoneName", null);
                }
            } else if (!zoneNameSet.isEmpty()) {
                for (String znName : zoneNameList) {
                    if (!serviceMgr.isZoneAdmin(znName) && !serviceMgr.isZoneAuditor(znName)) {
                        throw restErrorUtil.createRESTException(HttpServletResponse.SC_FORBIDDEN, "User is not the zone admin or zone auditor of zone " + znName, true);
                    }
                }
            }
        }

        if (RangerBizUtil.AUDIT_STORE_SOLR.equalsIgnoreCase(xaBizUtil.getAuditDBType())) {
            return solrAccessAuditsService.searchXAccessAudits(searchCriteria);
        } else if (RangerBizUtil.AUDIT_STORE_ELASTIC_SEARCH.equalsIgnoreCase(xaBizUtil.getAuditDBType())) {
            return elasticSearchAccessAuditsService.searchXAccessAudits(searchCriteria);
        } else if (RangerBizUtil.AUDIT_STORE_CLOUD_WATCH.equalsIgnoreCase(xaBizUtil.getAuditDBType())) {
            return cloudWatchAccessAuditsService.searchXAccessAudits(searchCriteria);
        } else {
            return xAccessAuditService.searchXAccessAudits(searchCriteria);
        }
    }

    public VXTrxLogList getTransactionReport(String transactionId) {
        List<VXTrxLogV2> trxLogsV2 = xTrxLogService.findByTransactionId(transactionId);
        List<VXTrxLog>   trxLogs   = new ArrayList<>();
        long             nextLogId = 1;

        for (VXTrxLogV2 trxLogV2 : trxLogsV2) {
            ObjectChangeInfo objChangeInfo = trxLogV2.getChangeInfo();

            if (objChangeInfo == null || CollectionUtils.isEmpty(objChangeInfo.getAttributes())) {
                VXTrxLog trxLog = VXTrxLogV2.toVXTrxLog(trxLogV2);

                trxLog.setId(nextLogId++);

                trxLogs.add(trxLog);
            } else {
                for (AttributeChangeInfo attrChangeInfo : objChangeInfo.getAttributes()) {
                    VXTrxLog trxLog = VXTrxLogV2.toVXTrxLog(trxLogV2);

                    trxLog.setId(nextLogId++);
                    trxLog.setAttributeName(attrChangeInfo.getAttributeName());
                    trxLog.setPreviousValue(attrChangeInfo.getOldValue());
                    trxLog.setNewValue(attrChangeInfo.getNewValue());

                    trxLogs.add(trxLog);
                }
            }
        }

        return new VXTrxLogList(validateXXTrxLogList(trxLogs));
    }

    public List<VXTrxLog> validateXXTrxLogList(List<VXTrxLog> xTrxLogList) {
        List<VXTrxLog> vXTrxLogs = new ArrayList<>();

        for (VXTrxLog vXTrxLog : xTrxLogList) {
            if (vXTrxLog.getPreviousValue() == null || "null".equalsIgnoreCase(vXTrxLog.getPreviousValue())) {
                vXTrxLog.setPreviousValue("");
            }

            if (vXTrxLog.getNewValue() == null || "null".equalsIgnoreCase(vXTrxLog.getNewValue())) {
                vXTrxLog.setNewValue("");
            }

            if (vXTrxLog.getAttributeName() != null && "Password".equalsIgnoreCase(vXTrxLog.getAttributeName())) {
                vXTrxLog.setPreviousValue("*********");
                vXTrxLog.setNewValue("***********");
            }

            if (vXTrxLog.getAttributeName() != null && "Connection Configurations".equalsIgnoreCase(vXTrxLog.getAttributeName())) {
                if (vXTrxLog.getPreviousValue() != null && vXTrxLog.getPreviousValue().contains("password")) {
                    String   tempPreviousStr = vXTrxLog.getPreviousValue();
                    String[] tempPreviousArr = vXTrxLog.getPreviousValue().split(",");

                    for (String tempPrevious : tempPreviousArr) {
                        if (tempPrevious.contains("{\"password") && tempPrevious.contains("}")) {
                            vXTrxLog.setPreviousValue(tempPreviousStr.replace(tempPrevious, "{\"password\":\"*****\"}"));
                            break;
                        } else if (tempPrevious.contains("{\"password")) {
                            vXTrxLog.setPreviousValue(tempPreviousStr.replace(tempPrevious, "{\"password\":\"*****\""));
                            break;
                        } else if (tempPrevious.contains("\"password") && tempPrevious.contains("}")) {
                            vXTrxLog.setPreviousValue(tempPreviousStr.replace(tempPrevious, "\"password\":\"******\"}"));
                            break;
                        } else if (tempPrevious.contains("\"password")) {
                            vXTrxLog.setPreviousValue(tempPreviousStr.replace(tempPrevious, "\"password\":\"******\""));
                            break;
                        }
                    }
                }

                if (vXTrxLog.getNewValue() != null && vXTrxLog.getNewValue().contains("password")) {
                    String   tempNewStr = vXTrxLog.getNewValue();
                    String[] tempNewArr = vXTrxLog.getNewValue().split(",");

                    for (String tempNew : tempNewArr) {
                        if (tempNew.contains("{\"password") && tempNew.contains("}")) {
                            vXTrxLog.setNewValue(tempNewStr.replace(tempNew, "{\"password\":\"*****\"}"));
                            break;
                        } else if (tempNew.contains("{\"password")) {
                            vXTrxLog.setNewValue(tempNewStr.replace(tempNew, "{\"password\":\"*****\""));
                            break;
                        } else if (tempNew.contains("\"password") && tempNew.contains("}")) {
                            vXTrxLog.setNewValue(tempNewStr.replace(tempNew, "\"password\":\"******\"}"));
                            break;
                        } else if (tempNew.contains("\"password")) {
                            vXTrxLog.setNewValue(tempNewStr.replace(tempNew, "\"password\":\"******\""));
                            break;
                        }
                    }
                }
            }

            vXTrxLogs.add(vXTrxLog);
        }

        return vXTrxLogs;
    }

    public VXTrxLogV2List getTransactionReportV2(String transactionId) {
        List<VXTrxLogV2> trxLogsV2 = xTrxLogService.findByTransactionId(transactionId);

        return new VXTrxLogV2List(validateXXTrxLogV2List(trxLogsV2));
    }

    public List<VXTrxLogV2> validateXXTrxLogV2List(List<VXTrxLogV2> xTrxLogV2List) {
        List<VXTrxLogV2> vXTrxLogV2s = new ArrayList<>();

        for (VXTrxLogV2 vXTrxLogV2 : xTrxLogV2List) {
            ObjectChangeInfo          objectChangeInfo = vXTrxLogV2.getChangeInfo();
            List<AttributeChangeInfo> attrChanges      = (objectChangeInfo == null || objectChangeInfo.getAttributes() == null) ? Collections.emptyList() : objectChangeInfo.getAttributes();

            for (AttributeChangeInfo attrChangeInfo : attrChanges) {
                if (attrChangeInfo.getOldValue() == null || "null".equalsIgnoreCase(attrChangeInfo.getOldValue())) {
                    attrChangeInfo.setOldValue("");
                }

                if (attrChangeInfo.getNewValue() == null || "null".equalsIgnoreCase(attrChangeInfo.getNewValue())) {
                    attrChangeInfo.setNewValue("");
                }

                if ("Password".equalsIgnoreCase(attrChangeInfo.getAttributeName())) {
                    attrChangeInfo.setOldValue("*********");
                    attrChangeInfo.setNewValue("***********");
                }

                if ("Connection Configurations".equalsIgnoreCase(attrChangeInfo.getAttributeName())) {
                    if (attrChangeInfo.getOldValue() != null && attrChangeInfo.getOldValue().contains("password")) {
                        String   tempPreviousStr = attrChangeInfo.getOldValue();
                        String[] tempPreviousArr = attrChangeInfo.getOldValue().split(",");

                        for (String tempPrevious : tempPreviousArr) {
                            if (tempPrevious.contains("{\"password") && tempPrevious.contains("}")) {
                                attrChangeInfo.setOldValue(tempPreviousStr.replace(tempPrevious, "{\"password\":\"*****\"}"));
                                break;
                            } else if (tempPrevious.contains("{\"password")) {
                                attrChangeInfo.setOldValue(tempPreviousStr.replace(tempPrevious, "{\"password\":\"*****\""));
                                break;
                            } else if (tempPrevious.contains("\"password") && tempPrevious.contains("}")) {
                                attrChangeInfo.setOldValue(tempPreviousStr.replace(tempPrevious, "\"password\":\"******\"}"));
                                break;
                            } else if (tempPrevious.contains("\"password")) {
                                attrChangeInfo.setOldValue(tempPreviousStr.replace(tempPrevious, "\"password\":\"******\""));
                                break;
                            }
                        }
                    }

                    if (attrChangeInfo.getNewValue() != null && attrChangeInfo.getNewValue().contains("password")) {
                        String   tempNewStr = attrChangeInfo.getNewValue();
                        String[] tempNewArr = attrChangeInfo.getNewValue().split(",");

                        for (String tempNew : tempNewArr) {
                            if (tempNew.contains("{\"password") && tempNew.contains("}")) {
                                attrChangeInfo.setNewValue(tempNewStr.replace(tempNew, "{\"password\":\"*****\"}"));
                                break;
                            } else if (tempNew.contains("{\"password")) {
                                attrChangeInfo.setNewValue(tempNewStr.replace(tempNew, "{\"password\":\"*****\""));
                                break;
                            } else if (tempNew.contains("\"password") && tempNew.contains("}")) {
                                attrChangeInfo.setNewValue(tempNewStr.replace(tempNew, "\"password\":\"******\"}"));
                                break;
                            } else if (tempNew.contains("\"password")) {
                                attrChangeInfo.setNewValue(tempNewStr.replace(tempNew, "\"password\":\"******\""));
                                break;
                            }
                        }
                    }
                }
            }

            vXTrxLogV2s.add(vXTrxLogV2);
        }

        return vXTrxLogV2s;
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.apache.ranger.biz.AssetMgrBase#searchXPolicyExportAudits(org.apache.ranger.
     * common.SearchCriteria)
     */
    @Override
    public VXPolicyExportAuditList searchXPolicyExportAudits(SearchCriteria searchCriteria) {
        if (searchCriteria == null) {
            searchCriteria = new SearchCriteria();
        }

        if (searchCriteria.getParamList() != null && !searchCriteria.getParamList().isEmpty()) {
            int      clientTimeOffsetInMinute = RestUtil.getClientTimeOffset();
            DateUtil dateUtil                 = new DateUtil();

            if (searchCriteria.getParamList().containsKey("startDate")) {
                Date temp = (Date) searchCriteria.getParamList().get("startDate");

                temp = dateUtil.getDateFromGivenDate(temp, 0, 0, 0, 0);
                temp = dateUtil.addTimeOffset(temp, clientTimeOffsetInMinute);

                searchCriteria.getParamList().put("startDate", temp);
            }
            if (searchCriteria.getParamList().containsKey("endDate")) {
                Date temp = (Date) searchCriteria.getParamList().get("endDate");

                temp = dateUtil.getDateFromGivenDate(temp, 0, 23, 59, 59);
                temp = dateUtil.addTimeOffset(temp, clientTimeOffsetInMinute);

                searchCriteria.getParamList().put("endDate", temp);
            }
        }

        return xPolicyExportAuditService.searchXPolicyExportAudits(searchCriteria);
    }

    public VXUgsyncAuditInfoList getUgsyncAudits(SearchCriteria searchCriteria) {
        if (!msBizUtil.hasModuleAccess(RangerConstants.MODULE_AUDIT)) {
            throw restErrorUtil.createRESTException(HttpServletResponse.SC_FORBIDDEN, "User is not having permissions on the " + RangerConstants.MODULE_AUDIT + " module.", true);
        }

        if (searchCriteria == null) {
            searchCriteria = new SearchCriteria();
        }

        if (searchCriteria.getParamList() != null && !searchCriteria.getParamList().isEmpty()) {
            int      clientTimeOffsetInMinute = RestUtil.getClientTimeOffset();
            DateUtil dateUtil                 = new DateUtil();
            if (searchCriteria.getParamList().containsKey("startDate")) {
                Date temp = (Date) searchCriteria.getParamList().get("startDate");

                temp = dateUtil.getDateFromGivenDate(temp, 0, 0, 0, 0);
                temp = dateUtil.addTimeOffset(temp, clientTimeOffsetInMinute);

                searchCriteria.getParamList().put("startDate", temp);
            }
            if (searchCriteria.getParamList().containsKey("endDate")) {
                Date temp = (Date) searchCriteria.getParamList().get("endDate");

                temp = dateUtil.getDateFromGivenDate(temp, 0, 23, 59, 59);
                temp = dateUtil.addTimeOffset(temp, clientTimeOffsetInMinute);

                searchCriteria.getParamList().put("endDate", temp);
            }
        }

        if (searchCriteria.getSortType() == null) {
            searchCriteria.setSortType("desc");
        } else if (!"asc".equalsIgnoreCase(searchCriteria.getSortType()) && !"desc".equalsIgnoreCase(searchCriteria.getSortType())) {
            searchCriteria.setSortType("desc");
        }

        return xUgsyncAuditInfoService.searchXUgsyncAuditInfoList(searchCriteria);
    }

    public VXUgsyncAuditInfoList getUgsyncAuditsBySyncSource(String syncSource) {
        if (!msBizUtil.hasModuleAccess(RangerConstants.MODULE_AUDIT)) {
            throw restErrorUtil.createRESTException(HttpServletResponse.SC_FORBIDDEN, "User is not having permissions on the " + RangerConstants.MODULE_AUDIT + " module.", true);
        }

        if (syncSource != null && !syncSource.trim().isEmpty()) {
            return xUgsyncAuditInfoService.searchXUgsyncAuditInfoBySyncSource(syncSource);
        } else {
            throw restErrorUtil.createRESTException("Please provide a valid syncSource", MessageEnums.INVALID_INPUT_DATA);
        }
    }

    @SuppressWarnings("unchecked")
    private HashMap<String, Object> populatePermMap(VXResource xResource, HashMap<String, Object> resourceMap, int assetType) {
        List<VXPermMap> xPermMapList = xResource.getPermMapList();
        Set<Long>       groupList    = new HashSet<>();

        for (VXPermMap xPermMap : xPermMapList) {
            groupList.add(xPermMap.getId());
        }

        List<HashMap<String, Object>> sortedPermMapGroupList = new ArrayList<>();

        // Loop for adding group perms
        for (VXPermMap xPermMap : xPermMapList) {
            String groupKey = xPermMap.getPermGroup();

            if (groupKey != null) {
                boolean found = false;

                for (HashMap<String, Object> sortedPermMap : sortedPermMapGroupList) {
                    if (sortedPermMap.containsValue(groupKey)) {
                        found = true;

                        Long groupId = xPermMap.getGroupId();
                        Long userId  = xPermMap.getUserId();

                        if (groupId != null) {
                            Set<String> groups = (Set<String>) sortedPermMap.get("groups");

                            if (groups != null) {
                                groups.add(xPermMap.getGroupName());

                                sortedPermMap.put("groups", groups);
                            }
                        } else if (userId != null) {
                            Set<String> users = (Set<String>) sortedPermMap.get("users");

                            if (users != null) {
                                users.add(xPermMap.getUserName());

                                sortedPermMap.put("users", users);
                            }
                        }

                        Set<String> access = (Set<String>) sortedPermMap.get("access");
                        String      perm   = AppConstants.getLabelFor_XAPermType(xPermMap.getPermType());

                        access.add(perm);

                        sortedPermMap.put("access", access);
                    }
                }
                if (!found) {
                    HashMap<String, Object> sortedPermMap = new HashMap<>();

                    sortedPermMap.put("groupKey", xPermMap.getPermGroup());

                    Set<String> permSet = new HashSet<>();
                    String      perm    = AppConstants.getLabelFor_XAPermType(xPermMap.getPermType());

                    permSet.add(perm);

                    sortedPermMap.put("access", permSet);

                    if (assetType == AppConstants.ASSET_KNOX) {
                        String[] ipAddrList = new String[0];

                        if (xPermMap.getIpAddress() != null) {
                            ipAddrList = xPermMap.getIpAddress().split(",");

                            sortedPermMap.put("ipAddress", ipAddrList);
                        } else {
                            sortedPermMap.put("ipAddress", ipAddrList);
                        }
                    }

                    Long groupId = xPermMap.getGroupId();
                    Long userId  = xPermMap.getUserId();

                    if (groupId != null) {
                        Set<String> groupSet = new HashSet<>();
                        String      group    = xPermMap.getGroupName();

                        groupSet.add(group);

                        sortedPermMap.put("groups", groupSet);
                    } else if (userId != null) {
                        Set<String> userSet = new HashSet<>();
                        String      user    = xPermMap.getUserName();

                        userSet.add(user);

                        sortedPermMap.put("users", userSet);
                    }

                    sortedPermMapGroupList.add(sortedPermMap);
                }
            }
        }

        for (HashMap<String, Object> sortedPermMap : sortedPermMapGroupList) {
            sortedPermMap.remove("groupKey");
        }

        for (HashMap<String, Object> sortedPermMap : sortedPermMapGroupList) {
            sortedPermMap.remove("groupKey");
        }

        resourceMap.put("permission", sortedPermMapGroupList);

        return resourceMap;
    }

    private String getBooleanValue(int elementValue) {
        if (elementValue == 1) {
            return "1"; // BOOL_TRUE
        }

        return "0"; // BOOL_FALSE
    }

    private void createOrUpdatePluginInfo(final RangerPluginInfo pluginInfo, int entityType, final int httpCode, String clusterName) {
        logger.debug("==> createOrUpdatePluginInfo(pluginInfo = {}, isPolicyDownloadRequest = {}, httpCode = {})", pluginInfo, isPolicyDownloadRequest(entityType), httpCode);

        final boolean  isTagVersionResetNeeded;
        final Runnable commitWork;

        if (httpCode == HttpServletResponse.SC_NOT_MODIFIED) {
            RangerPluginInfo dbObj    = null;
            Long pluginActivationTime = null;
            Long dbLastActivationTime = null;

            if (StringUtils.isNotBlank(pluginInfo.getServiceName())) {
                XXPluginInfo xObj = rangerDaoManager.getXXPluginInfo().find(pluginInfo.getServiceName(), pluginInfo.getHostName(), pluginInfo.getAppType());
                if (xObj != null) {
                    dbObj = pluginInfoService.populateViewObject(xObj);
                }
            }

            // Create or update PluginInfo record after transaction is completed. If it is created in-line here
            // then the TransactionManager will roll-back the changes because the HTTP return code is
            // HttpServletResponse.SC_NOT_MODIFIED

            switch (entityType) {
                case RangerPluginInfo.ENTITY_TYPE_POLICIES:
                    isTagVersionResetNeeded = rangerDaoManager.getXXService().findAssociatedTagService(pluginInfo.getServiceName()) == null;

                    pluginActivationTime = pluginInfo.getPolicyActivationTime();
                    dbLastActivationTime = dbObj != null ? dbObj.getPolicyActivationTime() : null;
                    break;
                case RangerPluginInfo.ENTITY_TYPE_TAGS:
                    isTagVersionResetNeeded = false;

                    pluginActivationTime = pluginInfo.getTagActivationTime();
                    dbLastActivationTime = dbObj != null ? dbObj.getTagActivationTime() : null;
                    break;
                case RangerPluginInfo.ENTITY_TYPE_ROLES:
                    isTagVersionResetNeeded = false;

                    pluginActivationTime = pluginInfo.getRoleActivationTime();
                    dbLastActivationTime = dbObj != null ? dbObj.getRoleActivationTime() : null;
                    break;
                case RangerPluginInfo.ENTITY_TYPE_USERSTORE:
                    isTagVersionResetNeeded = false;

                    pluginActivationTime = pluginInfo.getUserStoreActivationTime();
                    dbLastActivationTime = dbObj != null ? dbObj.getUserStoreActivationTime() : null;
                    break;
                case RangerPluginInfo.ENTITY_TYPE_GDS:
                    isTagVersionResetNeeded = false;

                    pluginActivationTime = pluginInfo.getGdsActivationTime();
                    dbLastActivationTime = dbObj != null ? dbObj.getGdsActivationTime() : null;
                    break;
                default:
                    isTagVersionResetNeeded = false;
                    break;
            }

            boolean isLastActivationTimeUpdateNeeded = pluginActivationTime != null && pluginActivationTime > 0 && (dbLastActivationTime == null || !dbLastActivationTime.equals(pluginActivationTime));

            if (!pluginActivityAuditLogNotModified && !isLastActivationTimeUpdateNeeded) {
                logger.debug("Not logging HttpServletResponse. SC_NOT_MODIFIED. To enable, set configuration: {}=true", PROP_PLUGIN_ACTIVITY_AUDIT_NOT_MODIFIED);

                commitWork = null;
            } else {
                commitWork = () -> doCreateOrUpdateXXPluginInfo(pluginInfo, entityType, isTagVersionResetNeeded, clusterName);
            }
        } else if (httpCode == HttpServletResponse.SC_NOT_FOUND) {
            if ((isPolicyDownloadRequest(entityType) && (pluginInfo.getPolicyActiveVersion() == null || pluginInfo.getPolicyActiveVersion() == -1))
                    || (isTagDownloadRequest(entityType) && (pluginInfo.getTagActiveVersion() == null || pluginInfo.getTagActiveVersion() == -1))
                    || (isRoleDownloadRequest(entityType) && (pluginInfo.getRoleActiveVersion() == null || pluginInfo.getRoleActiveVersion() == -1))
                    || (isUserStoreDownloadRequest(entityType) && (pluginInfo.getUserStoreActiveVersion() == null || pluginInfo.getUserStoreActiveVersion() == -1))
                    || (isGdsDownloadRequest(entityType) && (pluginInfo.getGdsActiveVersion() == null || pluginInfo.getGdsActiveVersion() == -1))) {
                commitWork = () -> doDeleteXXPluginInfo(pluginInfo);
            } else {
                commitWork = () -> doCreateOrUpdateXXPluginInfo(pluginInfo, entityType, false, clusterName);
            }
        } else {
            isTagVersionResetNeeded = false;

            commitWork = () -> doCreateOrUpdateXXPluginInfo(pluginInfo, entityType, isTagVersionResetNeeded, clusterName);
        }

        if (commitWork != null) {
            if (pluginActivityAuditCommitInline) {
                transactionSynchronizationAdapter.executeOnTransactionCompletion(commitWork);
            } else {
                transactionSynchronizationAdapter.executeAsyncOnTransactionComplete(commitWork);
            }
        }

        logger.debug("<== createOrUpdatePluginInfo(pluginInfo = {}, isPolicyDownloadRequest = {}, httpCode = {})", pluginInfo, isPolicyDownloadRequest(entityType), httpCode);
    }

    private XXPluginInfo doCreateOrUpdateXXPluginInfo(RangerPluginInfo pluginInfo, int entityType, final boolean isTagVersionResetNeeded, String clusterName) {
        XXPluginInfo ret = null;

        if (StringUtils.isNotBlank(pluginInfo.getServiceName())) {
            XXPluginInfo xObj = rangerDaoManager.getXXPluginInfo().find(pluginInfo.getServiceName(), pluginInfo.getHostName(), pluginInfo.getAppType());

            if (xObj == null) {
                Map<String, String> infoMap = pluginInfo.getInfo();

                if (!stringUtil.isEmpty(clusterName) && infoMap != null) {
                    infoMap.put(SearchFilter.CLUSTER_NAME, clusterName);

                    pluginInfo.setInfo(infoMap);
                }

                // ranger-admin is restarted, plugin contains latest versions and no earlier record for this plug-in client
                if (isPolicyDownloadRequest(entityType)) {
                    if (pluginInfo.getPolicyDownloadedVersion() != null && pluginInfo.getPolicyDownloadedVersion().equals(pluginInfo.getPolicyActiveVersion())) {
                        // This is our best guess of when policies may have been downloaded
                        pluginInfo.setPolicyDownloadTime(pluginInfo.getPolicyActivationTime());
                    }
                } else if (isTagDownloadRequest(entityType)) {
                    if (pluginInfo.getTagDownloadedVersion() != null && pluginInfo.getTagDownloadedVersion().equals(pluginInfo.getTagActiveVersion())) {
                        // This is our best guess of when tags may have been downloaded
                        pluginInfo.setTagDownloadTime(pluginInfo.getTagActivationTime());
                    }
                } else if (isRoleDownloadRequest(entityType)) {
                    if (pluginInfo.getRoleDownloadTime() != null && pluginInfo.getRoleDownloadedVersion().equals(pluginInfo.getRoleActiveVersion())) {
                        // This is our best guess of when role may have been downloaded
                        pluginInfo.setRoleDownloadTime(pluginInfo.getRoleActivationTime());
                    }
                } else if (isUserStoreDownloadRequest(entityType)) {
                    if (pluginInfo.getUserStoreDownloadTime() != null && pluginInfo.getUserStoreDownloadedVersion().equals(pluginInfo.getUserStoreActiveVersion())) {
                        // This is our best guess of when users and groups may have been downloaded
                        pluginInfo.setUserStoreDownloadTime(pluginInfo.getUserStoreActivationTime());
                    }
                } else if (isGdsDownloadRequest(entityType)) {
                    if (pluginInfo.getGdsDownloadTime() != null && pluginInfo.getGdsDownloadedVersion().equals(pluginInfo.getGdsActiveVersion())) {
                        // This is our best guess of when GDS info may have been downloaded
                        pluginInfo.setGdsDownloadTime(pluginInfo.getGdsActivationTime());
                    }
                }

                pluginInfo.setAdminCapabilities(adminCapabilities);

                xObj = pluginInfoService.populateDBObject(pluginInfo);

                logger.debug("Creating RangerPluginInfo record for service-version");

                ret = rangerDaoManager.getXXPluginInfo().create(xObj);
            } else {
                boolean             needsUpdating = false;
                RangerPluginInfo    dbObj         = pluginInfoService.populateViewObject(xObj);
                Map<String, String> infoMap       = dbObj.getInfo();

                if (infoMap != null && !stringUtil.isEmpty(clusterName)) {
                    if (!stringUtil.isEmpty(infoMap.get(SearchFilter.CLUSTER_NAME)) && !stringUtil.equals(infoMap.get(SearchFilter.CLUSTER_NAME), clusterName)) {
                        infoMap.put(SearchFilter.CLUSTER_NAME, clusterName);

                        needsUpdating = true;
                    }
                }

                if (!dbObj.getIpAddress().equals(pluginInfo.getIpAddress())) {
                    dbObj.setIpAddress(pluginInfo.getIpAddress());

                    needsUpdating = true;
                }

                if (isPolicyDownloadRequest(entityType)) {
                    if (dbObj.getPolicyDownloadedVersion() == null || !dbObj.getPolicyDownloadedVersion().equals(pluginInfo.getPolicyDownloadedVersion())) {
                        dbObj.setPolicyDownloadedVersion(pluginInfo.getPolicyDownloadedVersion());
                        dbObj.setPolicyDownloadTime(pluginInfo.getPolicyDownloadTime());

                        needsUpdating = true;
                    }

                    Long   lastKnownPolicyVersion     = pluginInfo.getPolicyActiveVersion();
                    Long   lastPolicyActivationTime   = pluginInfo.getPolicyActivationTime();
                    String lastPluginCapabilityVector = pluginInfo.getPluginCapabilities();

                    if (lastKnownPolicyVersion != null && lastKnownPolicyVersion == -1) {
                        // First download request after plug-in's policy-refresher starts
                        dbObj.setPolicyDownloadTime(pluginInfo.getPolicyDownloadTime());

                        needsUpdating = true;
                    }

                    if (lastKnownPolicyVersion != null && lastKnownPolicyVersion > 0 && (dbObj.getPolicyActiveVersion() == null || !dbObj.getPolicyActiveVersion().equals(lastKnownPolicyVersion))) {
                        dbObj.setPolicyActiveVersion(lastKnownPolicyVersion);

                        needsUpdating = true;
                    }

                    if (lastPolicyActivationTime != null && lastPolicyActivationTime > 0 && (dbObj.getPolicyActivationTime() == null || !dbObj.getPolicyActivationTime().equals(lastPolicyActivationTime))) {
                        dbObj.setPolicyActivationTime(lastPolicyActivationTime);

                        needsUpdating = true;
                    }

                    if (lastPluginCapabilityVector != null && (dbObj.getPluginCapabilities() == null || !dbObj.getPluginCapabilities().equals(lastPluginCapabilityVector))) {
                        dbObj.setPluginCapabilities(lastPluginCapabilityVector);

                        needsUpdating = true;
                    }

                    if (dbObj.getAdminCapabilities() == null || !dbObj.getAdminCapabilities().equals(adminCapabilities)) {
                        dbObj.setAdminCapabilities(adminCapabilities);

                        needsUpdating = true;
                    }
                } else if (isTagDownloadRequest(entityType)) {
                    if (dbObj.getTagDownloadedVersion() == null || !dbObj.getTagDownloadedVersion().equals(pluginInfo.getTagDownloadedVersion())) {
                        // First download for tags after tag-service is associated with resource-service
                        dbObj.setTagDownloadedVersion(pluginInfo.getTagDownloadedVersion());
                        dbObj.setTagDownloadTime(pluginInfo.getTagDownloadTime());

                        needsUpdating = true;
                    }

                    Long lastKnownTagVersion   = pluginInfo.getTagActiveVersion();
                    Long lastTagActivationTime = pluginInfo.getTagActivationTime();

                    if (lastKnownTagVersion != null && lastKnownTagVersion == -1) {
                        // First download request after plug-in's tag-refresher restarts
                        dbObj.setTagDownloadTime(pluginInfo.getTagDownloadTime());

                        needsUpdating = true;
                    }

                    if (lastKnownTagVersion != null && lastKnownTagVersion > 0 && (dbObj.getTagActiveVersion() == null || !dbObj.getTagActiveVersion().equals(lastKnownTagVersion))) {
                        dbObj.setTagActiveVersion(lastKnownTagVersion);

                        needsUpdating = true;
                    }

                    if (lastTagActivationTime != null && lastTagActivationTime > 0 && (dbObj.getTagActivationTime() == null || !dbObj.getTagActivationTime().equals(lastTagActivationTime))) {
                        dbObj.setTagActivationTime(lastTagActivationTime);

                        needsUpdating = true;
                    }
                } else if (isRoleDownloadRequest(entityType)) {
                    if (dbObj.getRoleDownloadedVersion() == null || !dbObj.getRoleDownloadedVersion().equals(pluginInfo.getRoleDownloadedVersion())) {
                        dbObj.setRoleDownloadedVersion(pluginInfo.getRoleDownloadedVersion());
                        dbObj.setRoleDownloadTime(pluginInfo.getRoleDownloadTime());

                        needsUpdating = true;
                    }

                    Long lastKnownRoleVersion   = pluginInfo.getRoleActiveVersion();
                    Long lastRoleActivationTime = pluginInfo.getRoleActivationTime();

                    if (lastKnownRoleVersion != null && lastKnownRoleVersion == -1) {
                        dbObj.setRoleDownloadTime(pluginInfo.getRoleDownloadTime());

                        needsUpdating = true;
                    }

                    if (lastKnownRoleVersion != null && lastKnownRoleVersion > 0 && (dbObj.getRoleActiveVersion() == null || !dbObj.getRoleActiveVersion().equals(lastKnownRoleVersion))) {
                        dbObj.setRoleActiveVersion(lastKnownRoleVersion);

                        needsUpdating = true;
                    }

                    if (lastRoleActivationTime != null && lastRoleActivationTime > 0 && (dbObj.getRoleActivationTime() == null || !dbObj.getRoleActivationTime().equals(lastRoleActivationTime))) {
                        dbObj.setRoleActivationTime(lastRoleActivationTime);

                        needsUpdating = true;
                    }
                } else if (isUserStoreDownloadRequest(entityType)) {
                    if (dbObj.getUserStoreDownloadedVersion() == null || !dbObj.getUserStoreDownloadedVersion().equals(pluginInfo.getUserStoreDownloadedVersion())) {
                        dbObj.setUserStoreDownloadedVersion(pluginInfo.getUserStoreDownloadedVersion());
                        dbObj.setUserStoreDownloadTime(pluginInfo.getUserStoreDownloadTime());

                        needsUpdating = true;
                    }

                    Long lastKnownUserStoreVersion   = pluginInfo.getUserStoreActiveVersion();
                    Long lastUserStoreActivationTime = pluginInfo.getUserStoreActivationTime();

                    if (lastKnownUserStoreVersion != null && lastKnownUserStoreVersion == -1) {
                        dbObj.setUserStoreDownloadTime(pluginInfo.getUserStoreDownloadTime());

                        needsUpdating = true;
                    }

                    if (lastKnownUserStoreVersion != null && lastKnownUserStoreVersion > 0 && (dbObj.getUserStoreActiveVersion() == null || !dbObj.getUserStoreActiveVersion().equals(lastKnownUserStoreVersion))) {
                        dbObj.setUserStoreActiveVersion(lastKnownUserStoreVersion);

                        needsUpdating = true;
                    }

                    if (lastUserStoreActivationTime != null && lastUserStoreActivationTime > 0 && (dbObj.getUserStoreActivationTime() == null || !dbObj.getUserStoreActivationTime().equals(lastUserStoreActivationTime))) {
                        dbObj.setUserStoreActivationTime(lastUserStoreActivationTime);

                        needsUpdating = true;
                    }
                } else if (isGdsDownloadRequest(entityType)) {
                    if (dbObj.getGdsDownloadedVersion() == null || !dbObj.getGdsDownloadedVersion().equals(pluginInfo.getGdsDownloadedVersion())) {
                        dbObj.setGdsDownloadedVersion(pluginInfo.getGdsDownloadedVersion());
                        dbObj.setGdsDownloadTime(pluginInfo.getGdsDownloadTime());

                        needsUpdating = true;
                    }

                    Long lastKnownGdsVersion   = pluginInfo.getGdsActiveVersion();
                    Long lastGdsActivationTime = pluginInfo.getGdsActivationTime();

                    if (lastKnownGdsVersion != null && lastKnownGdsVersion == -1) {
                        dbObj.setGdsDownloadTime(pluginInfo.getGdsDownloadTime());

                        needsUpdating = true;
                    }

                    if (lastKnownGdsVersion != null && lastKnownGdsVersion > 0 && (dbObj.getGdsActiveVersion() == null || !dbObj.getGdsActiveVersion().equals(lastKnownGdsVersion))) {
                        dbObj.setGdsActiveVersion(lastKnownGdsVersion);

                        needsUpdating = true;
                    }

                    if (lastGdsActivationTime != null && lastGdsActivationTime > 0 && (dbObj.getGdsActivationTime() == null || !dbObj.getGdsActivationTime().equals(lastGdsActivationTime))) {
                        dbObj.setGdsActivationTime(lastGdsActivationTime);

                        needsUpdating = true;
                    }
                }

                if (isTagVersionResetNeeded) {
                    dbObj.setTagDownloadedVersion(null);
                    dbObj.setTagDownloadTime(null);
                    dbObj.setTagActiveVersion(null);
                    dbObj.setTagActivationTime(null);

                    needsUpdating = true;
                }

                if (needsUpdating) {
                    logger.debug("Updating XXPluginInfo record for service-version");

                    xObj = pluginInfoService.populateDBObject(dbObj);

                    ret = rangerDaoManager.getXXPluginInfo().update(xObj);
                }
            }
        } else {
            logger.error("Invalid parameters: pluginInfo={})", pluginInfo);
        }

        return ret;
    }

    private void doDeleteXXPluginInfo(RangerPluginInfo pluginInfo) {
        XXPluginInfo xObj = rangerDaoManager.getXXPluginInfo().find(pluginInfo.getServiceName(), pluginInfo.getHostName(), pluginInfo.getAppType());

        if (xObj != null) {
            rangerDaoManager.getXXPluginInfo().remove(xObj.getId());
        }
    }

    private String getRemoteAddress(final HttpServletRequest request) {
        String ret = null;

        if (request != null) {
            String xForwardedAddress = request.getHeader("X-Forwarded-For");

            if (StringUtils.isNotBlank(xForwardedAddress)) {
                String[] forwardedAddresses = xForwardedAddress.split(",");

                if (forwardedAddresses.length > 0) {
                    // Use first one. Hope it is the IP of the originating client
                    ret = forwardedAddresses[0].trim();
                }
            }

            if (ret == null) {
                ret = request.getRemoteAddr();
            }
        }

        return ret;
    }

    private boolean isPolicyDownloadRequest(int entityType) {
        return entityType == RangerPluginInfo.ENTITY_TYPE_POLICIES;
    }

    private boolean isTagDownloadRequest(int entityType) {
        return entityType == RangerPluginInfo.ENTITY_TYPE_TAGS;
    }

    private boolean isRoleDownloadRequest(int entityType) {
        return entityType == RangerPluginInfo.ENTITY_TYPE_ROLES;
    }

    private boolean isUserStoreDownloadRequest(int entityType) {
        return entityType == RangerPluginInfo.ENTITY_TYPE_USERSTORE;
    }

    private boolean isGdsDownloadRequest(int entityType) {
        return entityType == RangerPluginInfo.ENTITY_TYPE_GDS;
    }
}
