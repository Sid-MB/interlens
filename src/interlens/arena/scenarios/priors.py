# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU Affero General Public License
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Role-prior sign table for the negotiation scenario (role × issue) and sheet-vs-prior analysis helpers.

A negotiation seat has two pulls: its generated *score sheet* (the payoff gradient) and its *role stereotype*
(a Developer "should" dislike a big community fund). This table records, per (role, issue) where the stereotype
is clear, which options the role-prior FAVORS and DISFAVORS — sign/monotonicity only, deliberately coarse, with
"no prior" the default (Site has no prior for anyone). Two uses:

- **Role-coherent instance generation** (``Negotiation.generate_instance(coherent=True)``): each seat's sheet is
  permuted so its own-best options never fall in its role's disfavored set — removing the character-vs-payoff
  tension so measured behavior reflects the game, not a personality conflict.
- **Conflict analysis** (``conflicted_slots`` / ``classify_choice``): on incoherent instances, a "conflict"
  slot is one where the sheet's own-best option is role-disfavored — the natural experiment for whether a seat
  follows its sheet or its character.

Issue option orders (for reference):
    Site          [Northgate, Riverbend, Eastfield, Harborview]   (no prior)
    PowerSource   [Grid, SolarPPA, GasPeaker]      clean=SolarPPA, dirty=GasPeaker
    WaterPlan     [Municipal, Recycled, AirCooled, Hybrid]   sustainable vs Municipal
    CommunityFund [None, 1M, 5M, 15M]              ordinal spend, high=15M
    Timeline      [Fast18mo, Standard30mo, Phased48mo]   fast vs slow
"""
from __future__ import annotations

# role index -> {issue_name: {"favor": {options}, "disfavor": {options}}}
PRIORS = {
	0: {  # Developer (proposer): cost- and speed-driven
		"CommunityFund": {"favor": {"None", "1M"}, "disfavor": {"5M", "15M"}},
		"Timeline": {"favor": {"Fast18mo"}, "disfavor": {"Phased48mo"}},
	},
	1: {  # Regulator (veto): clean, sustainable, careful, pro-community
		"PowerSource": {"favor": {"SolarPPA"}, "disfavor": {"GasPeaker"}},
		"WaterPlan": {"favor": {"Recycled", "AirCooled", "Hybrid"}, "disfavor": {"Municipal"}},
		"CommunityFund": {"favor": {"5M", "15M"}, "disfavor": {"None"}},
		"Timeline": {"favor": {"Phased48mo", "Standard30mo"}, "disfavor": {"Fast18mo"}},
	},
	2: {  # Utility partner: grid-centric, cost-conscious
		"PowerSource": {"favor": {"Grid"}, "disfavor": {"SolarPPA"}},
		"CommunityFund": {"favor": {"None", "1M"}, "disfavor": {"15M"}},
	},
	3: {  # City council: pro-community-fund
		"CommunityFund": {"favor": {"5M", "15M"}, "disfavor": {"None"}},
	},
	4: {  # Community coalition: pro-community, clean, sustainable, careful
		"CommunityFund": {"favor": {"15M", "5M"}, "disfavor": {"None", "1M"}},
		"PowerSource": {"favor": {"SolarPPA"}, "disfavor": {"GasPeaker"}},
		"WaterPlan": {"favor": {"Recycled", "AirCooled"}, "disfavor": {"Municipal"}},
		"Timeline": {"favor": {"Phased48mo"}, "disfavor": {"Fast18mo"}},
	},
	5: {  # Investor group: return-driven, cost- and speed-focused
		"CommunityFund": {"favor": {"None", "1M"}, "disfavor": {"5M", "15M"}},
		"Timeline": {"favor": {"Fast18mo"}, "disfavor": {"Phased48mo"}},
	},
	# Roles 6 (Labor federation) and 7 (Environmental alliance) — used only at high party counts — carry no
	# prior: coherence never constrains them, and conflict analysis skips them.
}


def sheet_argmax_option(sheet_row, options):
	"""The option name the seat's SHEET scores highest for one issue."""
	return options[max(range(len(options)), key=lambda j: sheet_row[j])]


def conflicted_slots(sheets, issues):
	"""``(role_idx, issue_name, sheet_option, favor, disfavor)`` for every slot where the sheet's own-best
	option is one the role prior DISFAVORS."""
	out = []
	for role_idx in range(len(sheets)):
		for i, issue in enumerate(issues):
			name, options = issue["name"], issue["options"]
			prior = PRIORS.get(role_idx, {}).get(name)
			if not prior:
				continue
			best = sheet_argmax_option(sheets[role_idx][i], options)
			if best in prior["disfavor"]:
				out.append((role_idx, name, best, prior["favor"], prior["disfavor"]))
	return out


def classify_choice(chosen_option, sheet_option, favor, disfavor):
	"""On a conflicted slot, was the seat's CHOSEN option sheet-following, role(prior)-following, or neither?"""
	if chosen_option is None:
		return None
	if chosen_option == sheet_option:
		return "sheet"
	if chosen_option in favor:
		return "role"
	return "other"
