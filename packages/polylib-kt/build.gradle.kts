import java.math.BigDecimal
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    kotlin("jvm") version "2.4.20"
    `java-library`
    `maven-publish`
    jacoco
}

group = "dev.polylib"
version = "0.1.0"

repositories {
    mavenCentral()
}

kotlin {
    jvmToolchain(21)
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.release.set(17)
}

sourceSets {
    main {
        kotlin.srcDir("src/generated/kotlin")
        resources.srcDir("src/generated/resources")
    }
}

dependencies {
    api("net.java.dev.jna:jna:5.17.0")

    testImplementation(platform("org.junit:junit-bom:5.13.4"))
    testImplementation(platform("io.cucumber:cucumber-bom:7.34.9"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testImplementation("org.junit.platform:junit-platform-suite")
    testImplementation("io.cucumber:cucumber-java")
    testImplementation("io.cucumber:cucumber-junit-platform-engine")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.named<Jar>("jar") {
    manifest {
        attributes(
            "Implementation-Title" to "polylib",
            "Implementation-Version" to project.version.toString(),
        )
    }
}

tasks.register("writeRuntimeClasspath") {
    val outputFile = layout.buildDirectory.file("runtime-classpath.txt")
    val runtimeFiles = configurations.runtimeClasspath
    outputs.file(outputFile)
    doLast {
        val file = outputFile.get().asFile
        file.parentFile.mkdirs()
        file.writeText(runtimeFiles.get().files.joinToString(File.pathSeparator) { it.absolutePath })
    }
}

val jacocoFilteredClasses =
    sourceSets.main.get().output.asFileTree.matching {
        exclude("dev/polylib/ffi/**")
    }

tasks.jacocoTestReport {
    dependsOn(tasks.test)
    classDirectories.setFrom(jacocoFilteredClasses)
    reports {
        xml.required.set(true)
        xml.outputLocation.set(rootProject.layout.projectDirectory.file("../../coverage/kotlin/jacoco.xml"))
        html.required.set(false)
        csv.required.set(false)
    }
}

tasks.jacocoTestCoverageVerification {
    dependsOn(tasks.test)
    classDirectories.setFrom(jacocoFilteredClasses)
    violationRules {
        rule {
            limit {
                counter = "LINE"
                value = "COVEREDRATIO"
                minimum = BigDecimal("0.90")
            }
        }
    }
}

publishing {
    publications {
        create<MavenPublication>("maven") {
            from(components["java"])
            artifactId = "polylib"
            pom {
                name.set("polylib")
                description.set("Idiomatic Kotlin/JVM facade over Rust polylib-core via UniFFI and JNA.")
                licenses {
                    license {
                        name.set("MIT License")
                        url.set("https://opensource.org/licenses/MIT")
                    }
                }
            }
        }
    }
    repositories {
        maven {
            name = "GitHubPackages"
            val ghRepo = System.getenv("GITHUB_REPOSITORY") ?: "your-org/polyglot-lib-template"
            url = uri("https://maven.pkg.github.com/$ghRepo")
            credentials {
                username = System.getenv("GITHUB_ACTOR") ?: ""
                password = System.getenv("GITHUB_TOKEN") ?: ""
            }
        }
        val mavenCentralUrl = System.getenv("MAVEN_CENTRAL_URL")
        if (!mavenCentralUrl.isNullOrBlank()) {
            maven {
                name = "MavenCentral"
                url = uri(mavenCentralUrl)
                credentials {
                    username = System.getenv("MAVEN_CENTRAL_USERNAME") ?: ""
                    password = System.getenv("MAVEN_CENTRAL_PASSWORD") ?: ""
                }
            }
        }
    }
}

tasks.test {
    useJUnitPlatform()
    val nativeReleaseDir = rootProject.projectDir.resolve("../../target/release").canonicalPath
    systemProperty("jna.library.path", nativeReleaseDir)
    testLogging {
        events("passed", "skipped", "failed")
    }
}
