package dev.polylib

import io.cucumber.junit.platform.engine.Constants.GLUE_PROPERTY_NAME
import io.cucumber.junit.platform.engine.Constants.PLUGIN_PROPERTY_NAME
import org.junit.platform.suite.api.ConfigurationParameter
import org.junit.platform.suite.api.IncludeEngines
import org.junit.platform.suite.api.SelectDirectories
import org.junit.platform.suite.api.Suite

@Suite
@IncludeEngines("cucumber")
@SelectDirectories("../../conformance")
@ConfigurationParameter(key = GLUE_PROPERTY_NAME, value = "dev.polylib")
@ConfigurationParameter(key = PLUGIN_PROPERTY_NAME, value = "pretty")
class ConformanceTest
