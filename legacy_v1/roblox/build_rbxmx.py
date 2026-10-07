"""Pack roblox/src/*.lua + BillboardData.lua into CyberpunkCity.rbxmx (drag into Studio)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# (instance name, class, source file, RunContext token: 0 Legacy, 1 Server, 2 Client)
ITEMS = [
    ("CyberpunkConfig", "ModuleScript", "src/CyberpunkConfig.lua", None),
    ("CyberpunkSetup", "ModuleScript", "src/CyberpunkSetup.lua", None),
    ("BillboardData", "ModuleScript", "BillboardData.lua", None),
    ("RunSetup", "Script", "src/RunSetup.server.lua", 0),
    ("CyberpunkAnimator", "Script", "src/CyberpunkAnimator.client.lua", 2),
]


def cdata(text):
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def main():
    out = [
        '<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">',
        '\t<Item class="Folder" referent="RBX0">',
        '\t\t<Properties><string name="Name">CyberpunkCity</string></Properties>',
    ]
    for i, (name, cls, path, run_context) in enumerate(ITEMS, start=1):
        with open(os.path.join(HERE, path), encoding="utf-8") as f:
            src = f.read()
        out.append(f'\t\t<Item class="{cls}" referent="RBX{i}">')
        out.append("\t\t\t<Properties>")
        out.append(f'\t\t\t\t<string name="Name">{name}</string>')
        if run_context is not None:
            out.append('\t\t\t\t<bool name="Disabled">false</bool>')
            out.append(f'\t\t\t\t<token name="RunContext">{run_context}</token>')
        out.append(f'\t\t\t\t<ProtectedString name="Source">{cdata(src)}</ProtectedString>')
        out.append("\t\t\t</Properties>")
        out.append("\t\t</Item>")
    out += ["\t</Item>", "</roblox>", ""]
    dest = os.path.join(HERE, "CyberpunkCity.rbxmx")
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("wrote", dest)


if __name__ == "__main__":
    main()
