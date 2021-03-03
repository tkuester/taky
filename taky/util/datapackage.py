import os

from lxml import etree


def build_pref(pref_fp, prefs):
    """
    Build an XML preference file
    """
    prefs_xml = etree.Element("preferences")
    for (name, pref) in prefs.items():
        pref_xml = etree.Element(
            "preference",
            attrib={
                "version": "1",
                "name": name,
            },
        )

        for (key, val) in pref.items():
            if isinstance(val, bool):
                v_type = "Boolean"
            elif isinstance(val, int):
                v_type = "Integer"
            elif isinstance(val, str):
                v_type = "String"

            entry = etree.Element(
                "entry", attrib={"key": key, "class": f"class java.lang.{v_type}"}
            )

            if isinstance(val, bool):
                entry.text = str(val).lower()
            else:
                entry.text = str(val)

            pref_xml.append(entry)

        prefs_xml.append(pref_xml)

    pref_fp.write(
        etree.tostring(
            prefs_xml, pretty_print=True, xml_declaration=True, standalone=True
        )
    )


def build_manifest(man_fp, cfg_params, contents):
    """
    Build a Datapackage manifest
    """
    # Build MissionPackageManifest root element
    mpm = etree.Element("MissionPackageManifest", attrib={"version": "2"})

    # Build Configuration element
    cfg_xml = etree.Element("Configuration")
    for (name, value) in cfg_params.items():
        cfg_xml.append(
            etree.Element(
                "Parameter",
                attrib={
                    "name": name,
                    "value": value,
                },
            )
        )
    mpm.append(cfg_xml)

    # Build Contents element
    cts = etree.Element("Contents")
    for name in contents:
        cts.append(
            etree.Element(
                "Content",
                attrib={"ignore": "false", "zipEntry": os.path.join("certs", name)},
            )
        )
    mpm.append(cts)

    # Write document
    man_fp.write(etree.tostring(mpm, pretty_print=True))
