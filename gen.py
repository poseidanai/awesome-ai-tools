# Builds README.md of poseidanai/awesome-ai-tools from tools.tsv (category, repo, description, featured)
import csv
rows = list(csv.reader(open("tools.tsv"), delimiter="\t"))
cats = [("creative", "🎨 Creative", "Make and edit video, images, voice, music and 3D."),
        ("marketing", "📈 Marketing", "SEO, content, ads, outreach and social posting."),
        ("build", "🛠️ Build", "Agents, automations, docs and dev tools that do real work.")]
out = ["# Awesome AI Tools", "",
       "[![Awesome](https://awesome.re/badge.svg)](https://awesome.re) [![License: CC0](https://img.shields.io/badge/license-CC0-blue.svg)](LICENSE)", "",
       "Open source AI tools that do one real job well, picked for creators, marketers and builders by [PoseidanAI](https://github.com/poseidanai).",
       "", "Every tool here is free to use, has a real license and is alive (pushed in the last months).",
       "", "**[See the live ranking at poseidanai.com/top →](https://poseidanai.com/top/)** Tools move up and down every day as people star them. Hover any tool there to see it in action.",
       "", "[![Live AI Tools Board](assets/live-board.png)](https://poseidanai.com/top/)",
       "", "🎬 = we made a video about it.", "", "## Contents", ""]
for k, title, _ in cats:
    anchor = "-" + title.split(" ", 1)[1].lower()
    out.append(f"- [{title}](#{anchor})")
out += ["- [Built with PoseidanAI](#built-with-poseidanai)", "- [Contributing](#contributing)", ""]
for k, title, blurb in cats:
    out += [f"## {title}", "", blurb, ""]
    mine = [r for r in rows if r[0] == k]
    keep = {r[1] for r in mine if r[3] == "y"}
    for r in mine:
        if len(keep) >= 30: break
        keep.add(r[1])
    for c, repo, desc, feat in mine:
        if repo not in keep:
            continue
        name = repo.split("/")[1]
        star = f"![stars](https://img.shields.io/github/stars/{repo}?style=flat&label=%E2%98%85&color=0a3664)"
        out.append(f"- [{name}](https://github.com/{repo}) {star}{' 🎬' if feat == 'y' else ''} - {desc}")
    out.append("")
out += ["## Built with PoseidanAI", "",
        "Projects people built on our open source tools. Built something? Add the badge to your README and open a PR to get listed here.", "",
        "```markdown", "[![Built with PoseidanAI](https://img.shields.io/badge/built%20with-PoseidanAI-0a3664)](https://github.com/poseidanai)", "```", "",
        "_Be the first one._", "",
        "## Contributing", "",
        "Know a tool that belongs here? Read [CONTRIBUTING.md](CONTRIBUTING.md) and open a PR. One tool per PR, one line, no affiliate links. Live ranking: [poseidanai.com/top](https://poseidanai.com/top/)", ""]
open("README.md", "w").write("\n".join(out))
print(len([r for r in rows]), "tools")
