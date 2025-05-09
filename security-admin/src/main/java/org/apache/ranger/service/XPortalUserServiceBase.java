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

package org.apache.ranger.service;

import org.apache.ranger.common.AppConstants;
import org.apache.ranger.common.SearchCriteria;
import org.apache.ranger.common.view.VTrxLogAttr;
import org.apache.ranger.entity.XXPortalUser;
import org.apache.ranger.view.VXPortalUser;
import org.apache.ranger.view.VXPortalUserList;

import java.util.ArrayList;
import java.util.List;

public abstract class XPortalUserServiceBase<T extends XXPortalUser, V extends VXPortalUser> extends AbstractAuditedResourceService<T, V> {
    public static final String NAME = "XPortalUser";

    public XPortalUserServiceBase() {
        super(AppConstants.CLASS_TYPE_USER_PROFILE);

        trxLogAttrs.put("loginId", new VTrxLogAttr("loginId", "Login ID", false, true));
        trxLogAttrs.put("status", new VTrxLogAttr("status", "Activation Status"));
        trxLogAttrs.put("firstName", new VTrxLogAttr("firstName", "First Name"));
        trxLogAttrs.put("lastName", new VTrxLogAttr("lastName", "Last Name"));
        trxLogAttrs.put("emailAddress", new VTrxLogAttr("emailAddress", "Email Address"));
        trxLogAttrs.put("publicScreenName", new VTrxLogAttr("publicScreenName", "Public Screen Name"));
    }

    /**
     * @param searchCriteria
     * @return
     */
    public VXPortalUserList searchXPortalUsers(SearchCriteria searchCriteria) {
        VXPortalUserList   returnList      = new VXPortalUserList();
        List<VXPortalUser> xPortalUserList = new ArrayList<>();
        List<T>            resultList      = searchResources(searchCriteria, searchFields, sortFields, returnList);

        // Iterate over the result list and create the return list
        for (T gjXPortalUser : resultList) {
            VXPortalUser vXPortalUser = populateViewBean(gjXPortalUser);

            xPortalUserList.add(vXPortalUser);
        }

        returnList.setVXPortalUsers(xPortalUserList);

        return returnList;
    }

    @Override
    protected T mapViewToEntityBean(V vObj, T mObj, int operationContext) {
        mObj.setFirstName(vObj.getFirstName());
        mObj.setLastName(vObj.getLastName());
        mObj.setPublicScreenName(vObj.getPublicScreenName());
        mObj.setLoginId(vObj.getLoginId());
        mObj.setPassword(vObj.getPassword());
        mObj.setEmailAddress(vObj.getEmailAddress());
        mObj.setStatus(vObj.getStatus());
        mObj.setUserSource(vObj.getUserSource());
        mObj.setNotes(vObj.getNotes());
        mObj.setOtherAttributes(vObj.getOtherAttributes());
        mObj.setSyncSource(vObj.getSyncSource());

        return mObj;
    }

    @Override
    protected V mapEntityToViewBean(V vObj, T mObj) {
        vObj.setFirstName(mObj.getFirstName());
        vObj.setLastName(mObj.getLastName());
        vObj.setPublicScreenName(mObj.getPublicScreenName());
        vObj.setLoginId(mObj.getLoginId());
        vObj.setPassword(mObj.getPassword());
        vObj.setEmailAddress(mObj.getEmailAddress());
        vObj.setStatus(mObj.getStatus());
        vObj.setUserSource(mObj.getUserSource());
        vObj.setNotes(mObj.getNotes());
        vObj.setOtherAttributes(mObj.getOtherAttributes());
        vObj.setSyncSource(mObj.getSyncSource());

        return vObj;
    }
}
