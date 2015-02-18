/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.ambari.server.checks;

import java.util.Collections;

import org.apache.ambari.server.ServiceNotFoundException;
import org.apache.ambari.server.controller.PrereqCheckRequest;
import org.apache.ambari.server.orm.dao.HostComponentStateDAO;
import org.apache.ambari.server.state.Cluster;
import org.apache.ambari.server.state.Clusters;
import org.apache.ambari.server.state.Service;
import org.apache.ambari.server.state.ServiceComponent;
import org.apache.ambari.server.state.ServiceComponentHost;
import org.apache.ambari.server.state.stack.PrereqCheckStatus;
import org.apache.ambari.server.state.stack.PrerequisiteCheck;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;

import com.google.inject.Provider;

/**
 * Unit tests for SecondaryNamenodeDeletedCheck
 *
 */
public class SecondaryNamenodeDeletedCheckTest {
  private final Clusters clusters = Mockito.mock(Clusters.class);
  private final HostComponentStateDAO hostComponentStateDAO = Mockito.mock(HostComponentStateDAO.class);

  private final SecondaryNamenodeDeletedCheck secondaryNamenodeDeletedCheck = new SecondaryNamenodeDeletedCheck();

  @Before
  public void setup() {
    secondaryNamenodeDeletedCheck.clustersProvider = new Provider<Clusters>() {

      @Override
      public Clusters get() {
        return clusters;
      }
    };

    secondaryNamenodeDeletedCheck.hostComponentStateDao = hostComponentStateDAO;
  }

  @Test
  public void testIsApplicable() throws Exception {
    final Cluster cluster = Mockito.mock(Cluster.class);
    Mockito.when(cluster.getClusterId()).thenReturn(1L);
    Mockito.when(clusters.getCluster("cluster")).thenReturn(cluster);

    final Service service = Mockito.mock(Service.class);
    Mockito.when(cluster.getService("HDFS")).thenReturn(service);
    Assert.assertTrue(secondaryNamenodeDeletedCheck.isApplicable(new PrereqCheckRequest("cluster")));

    Mockito.when(cluster.getService("HDFS")).thenThrow(new ServiceNotFoundException("no", "service"));
    Assert.assertFalse(secondaryNamenodeDeletedCheck.isApplicable(new PrereqCheckRequest("cluster")));
  }

  @Test
  public void testPerform() throws Exception {
    final Cluster cluster = Mockito.mock(Cluster.class);
    Mockito.when(cluster.getClusterId()).thenReturn(1L);
    Mockito.when(clusters.getCluster("cluster")).thenReturn(cluster);

    final Service service = Mockito.mock(Service.class);
    final ServiceComponent serviceComponent = Mockito.mock(ServiceComponent.class);
    Mockito.when(cluster.getService("HDFS")).thenReturn(service);
    Mockito.when(service.getServiceComponent("SECONDARY_NAMENODE")).thenReturn(serviceComponent);
    Mockito.when(serviceComponent.getServiceComponentHosts()).thenReturn(Collections.<String, ServiceComponentHost>singletonMap("host", null));

    PrerequisiteCheck check = new PrerequisiteCheck(null, null, null, null);
    secondaryNamenodeDeletedCheck.perform(check, new PrereqCheckRequest("cluster"));
    Assert.assertEquals(PrereqCheckStatus.FAIL, check.getStatus());

    Mockito.when(serviceComponent.getServiceComponentHosts()).thenReturn(Collections.<String, ServiceComponentHost> emptyMap());
    check = new PrerequisiteCheck(null, null, null, null);
    secondaryNamenodeDeletedCheck.perform(check, new PrereqCheckRequest("cluster"));
    Assert.assertEquals(PrereqCheckStatus.PASS, check.getStatus());
  }
}
