from canonical.runtime import retrieval_repository_manifest_bridge_v1 as b

def test_gemspec_name():
    text='Gem::Specification.new do |spec|\n  spec.name = "sidekiq"\nend'
    assert b.extract_identities("sidekiq.gemspec",text,"rubygems")==["sidekiq"]

def test_package_json():
    assert b.extract_identities("package.json",'{"name":"p-map"}',"npm")==["p-map"]

def test_cargo_toml():
    text='[package]\nname = "serde_json"\nversion = "1.0.0"\n'
    assert b.extract_identities("Cargo.toml",text,"cargo")==["serde_json"]

def test_composer():
    assert b.extract_identities("composer.json",'{"name":"symfony/http-client"}',"packagist")==["symfony/http-client"]

def test_nuget():
    assert b.extract_identities("x.nuspec","<package><metadata><id>Dapper</id></metadata></package>","nuget")==["Dapper"]
    assert b.extract_identities("x.csproj","<Project><PropertyGroup><PackageId>Serilog</PackageId></PropertyGroup></Project>","nuget")==["Serilog"]

def test_maven():
    text="<project><groupId>org.jsoup</groupId><artifactId>jsoup</artifactId></project>"
    assert b.extract_identities("pom.xml",text,"maven")==["org.jsoup:jsoup"]

if __name__=="__main__":
    test_gemspec_name();test_package_json();test_cargo_toml();test_composer();test_nuget();test_maven()
    print("test_retrieval_repository_manifest_bridge_v1: PASS")
