"""Words for the contamination system: the vanilla crime/police/court/prison
strings re-themed. Merged into the one TEXT overlay by survivors_text.py (a
second overlay of sovietEnglish.btf would just replace the first).
"""

FALLOUT = {
    # statistics and graphs
    2463: 'Contamination', 2759: 'How contamination will be affected',
    8093: 'Unswept contamination reports this year', 8094: 'Exposure cases this year',
    8095: 'Radiation sickness cases this year', 8096: 'Acute syndrome cases this year',
    54010: 'Contamination', 54038: 'Contamination', 67066: 'Contamination & quarantine',
    56100: 'Contamination reports', 56101: 'Sweep never reached the case', 56102: 'Household was not screened',
    56103: 'Board issued no assessment', 56105: 'Quarantine terms', 56108: 'Number of contamination cases',
    56106: 'This task force is unlikely to screen this case', 56107: 'This board is unlikely to assess this case',
    28866: 'Cases before the board', 28868: 'Currently in quarantine', 28869: 'In quarantine',
    28879: 'Containment', 28882: 'unassessed cases this year', 28883: 'unassessed cases last year',
    28884: 'containment breaches this year', 28885: 'containment breaches last year',
    28886: 'No recovery center with a free bed', 28890: 'reports that were never swept',
    28891: 'The contaminated site no longer exists', 28897: 'Take readings',
    # buildings
    6262: 'Decontamination Task Force', 6264: 'Radiology Board', 6265: 'Recovery Center', 6266: 'Reunification Office',
    6267: 'Decontamination Task Force (small)', 6268: 'Radiology Board (small)', 6269: 'Reunification Office (small)',
    9073: 'Decontamination Task Force', 9075: 'Radiology Board', 9076: 'Recovery Center', 9077: 'Reunification Office',
    3048: 'Quarantine bus', 3060: 'Geiger patrol car',
    # building windows
    37800: 'Missing task force staff and sweepers', 37801: 'Missing sweepers', 37802: 'Missing task force staff',
    37803: 'Missing radiology board', 37804: 'Missing recovery center', 37805: 'Task force staff', 37806: 'Sweepers',
    37807: 'Geiger patrol cars', 37808: 'Dose class', 37809: 'Screening', 37812: 'Contamination cases', 37813: 'Contaminated site:',
    37830: 'Exposure', 37835: 'Radiation sickness', 37840: 'Acute syndrome', 37853: 'Patients',
    38858: 'Missing board staff and physicians', 38859: 'Missing physicians', 38860: 'Missing board staff',
    38861: 'Board staff', 38862: 'Physicians',
    2332: 'Transfer up to 5 patients', 2333: 'Patients can be transferred only to another recovery center.',
    2621: 'Missing supplies for patients',
    3075: "Can't demolish building, some patients are still living there. Transfer them to a new home first!",
    54041: 'Arrival at a recovery center', 54052: 'Recovery center upbringing', 67117: 'Patients not working',
    # notifications
    15010: 'Sweep never arrived', 15013: 'Too many contaminated citizens',
    15060: 'Recently, a Geiger patrol failed to reach a contaminated site.',
    15070: 'Notification for the task force', 15073: 'Notification for citizen contamination level',
    15075: "When there aren't enough tutors in the shelter, the children living there grow up scavenging in the zones and contaminated.",
    15076: 'There are too many contaminated citizens living in this residential building or area.\n\nConsider building more task force stations, and make sure the sweepers screen every new case.',
    15085: 'Notify me when there are not enough medics', 15086: 'Not enough medics in the recovery center',
    15087: 'There are not enough medics in this recovery center. Containment will drop and patients may walk out still hot, spreading contamination.',
    15088: 'Too many unscreened cases', 15089: 'The task force is struggling to screen every case, leaving many households unswept.',
    15090: 'Notify me when unscreened cases are excessive', 15092: 'Board overwhelmed',
    15093: 'The radiology board is struggling with its caseload. This could be a shortage of physicians or too many cases. Some cases will be dropped and stay contaminated.',
    80524: 'If there are not enough workers in the shelter, the children grow up contaminated.',
    57020: 'For this feature to be available, you need to select the following when starting a new game: "Crime & Justice: Enabled"',
    # tutorial / campaign lines that mention the chain
    39734: 'Contamination and Government',
    39762: 'Build a Decontamination Task Force. Sweepers are needed to screen contaminated households.',
    39763: 'Purchase 4 Geiger patrol cars. Patrols are sent to contaminated sites.',
    39764: 'Build a small radiology board.\nScreening is not enough. Without a board no dose is assessed and the contaminated go back into the population.',
    39766: 'Invite survivors with higher education. Radiology boards need physicians.',
    39767: 'Build a recovery center.\nTo deal with contamination you need task forces to screen, boards to assess and recovery centers to quarantine. If one is missing, the chain fails.',
    39768: 'Buy a quarantine bus.\nPatients do not have to sit idle. Convalescent crews can be bussed to work - the hot jobs are the obvious place.',
    39769: "Build a children's shelter.\nWhen people go into quarantine or die early, someone has to take care of their children.",
    # editor / cheats
    60047: "Reset citizens' contamination level", 60048: "Increase citizens' contamination level",
    60050: 'Trigger an exposure case', 60051: 'Trigger a radiation sickness case', 60052: 'Trigger an acute syndrome case',
    # secret police -> reunification office (loyalty)
    11137: 'Reunification Office',
    11138: 'Outlines a new office tasked with measuring how far each household has come from the old regime. After this research, a Reunification Office can be established to read citizen loyalty to the new republic.',
    28892: "Reunification agents need to visit the citizen's home to display the household's loyalty level",
    28893: 'Reunification agents',
    36870: 'Loyalty assessment',
    39770: 'Build a Reunification Office.\nIts agents measure loyalty to the new republic. Without them you will not know who still answers to the old regime.',
    39772: 'Buy vehicles for the Reunification Office.\nAgents drive out to talk to households. Paint them black if you like the old ways.',
    # vehicle names
    5542: 'VAZ-2109 Geiger patrol', 5530: 'V24 Geiger patrol', 5535: 'B1000 quarantine bus', 5533: 'Nysa quarantine bus',
    5534: 'Ifa-W50 quarantine bus', 5545: 'FZK-A07 quarantine bus', 5586: 'IMV-1600 quarantine bus',
    5529: 'S1203 quarantine bus', 5536: 'A21F quarantine transport', 5537: 'A30 quarantine transport',
    5387: 'S100 (Geiger patrol)', 5528: 'GZ M21 (Geiger patrol)', 5543: 'Trabi 601 (Geiger patrol)', 5544: 'S120 Geiger patrol',
    5546: 'F 125 Geiger patrol', 5246: 'S1202 Geiger patrol',
}
