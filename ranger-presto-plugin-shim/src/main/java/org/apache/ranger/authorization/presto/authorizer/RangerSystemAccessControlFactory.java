/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.ranger.authorization.presto.authorizer;

import com.google.inject.Injector;
import com.google.inject.Scopes;
import io.airlift.bootstrap.Bootstrap;
import io.prestosql.spi.security.SystemAccessControl;
import io.prestosql.spi.security.SystemAccessControlFactory;

import java.util.Map;

import static io.airlift.configuration.ConfigBinder.configBinder;
import static java.util.Objects.requireNonNull;
import static org.apache.hadoop.thirdparty.com.google.common.base.Throwables.throwIfUnchecked;

public class RangerSystemAccessControlFactory implements SystemAccessControlFactory {
    private static final String NAME = "ranger";

    @Override
    public String getName() {
        return NAME;
    }

    @Override
    public SystemAccessControl create(Map<String, String> config) {
        requireNonNull(config, "config is null");

        try {
            Bootstrap app = new Bootstrap(binder -> {
                configBinder(binder).bindConfig(RangerConfig.class);
                binder.bind(RangerSystemAccessControl.class).in(Scopes.SINGLETON);
            });

            Injector injector = app
                    .strictConfig()
                    .doNotInitializeLogging()
                    .setRequiredConfigurationProperties(config)
                    .initialize();

            return injector.getInstance(RangerSystemAccessControl.class);
        } catch (Exception e) {
            throwIfUnchecked(e);
            throw new RuntimeException(e);
        }
    }
}
