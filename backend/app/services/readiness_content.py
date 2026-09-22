"""
readiness_content.py — De canonieke inhoud van de twee Readiness Checks.

DIT IS DE ENIGE BRON. De browserweergave op rhoderlanden.rhadix.nl en het
serverzijdige rapport worden allebei hieruit afgeleid:

    INHOUD ──┬─→ scripts/genereer_readiness_config.py → window.RG_READINESS in de HTML
             └─→ readiness_scoring.py / readiness_rapport.py → PDF en e-mail

Daardoor kunnen scherm en rapport per constructie niet uiteenlopen.

Herkomst: letterlijk overgenomen uit de vastgestelde website-baseline
`baseline-2026-09-21` (bestand `site/data-readiness.html`), machinaal
geextraheerd — niet overgetypt. `test_readiness_pariteit.py` bewijst dat de
hieruit gegenereerde configuratie byte-identiek is aan die baseline.

Inhoudelijk wijzigen mag uitsluitend op expliciete opdracht: de vragen,
antwoordmogelijkheden, grenswaarden, adviezen en rapportteksten zijn
vastgesteld en functioneel geaccepteerd.

Structuur
---------
answers      : [(label, punten)] — vier antwoordmogelijkheden, 3 t/m 0
cats         : [(ondergrens, bovengrens, categorie)] — bovenste band erft
               `top` van de check ("Datagereed" / "KIK-V-gereed")
positioning  : de drie treden check → rapport → onderzoek
checks       : per sleutel ("data" / "kikv") titel, top, kind, diensten,
               vier duidingen (een per band) en vijf dimensies
dims[i]      : name, q[3], advice, low, high, findings[3], strengths[3],
               optioneel `qa` en optioneel `extra`
qa[j]        : de vier antwoordlabels van vraag j, in de volgorde 3-2-1-0.
               Ontbreekt `qa`, dan gelden de globale labels uit `answers`.
               De Data Readiness Check heeft eigen labels per vraag; de
               KIK-V-check valt terug op de globale vier.
extra        : een vijfde antwoordmogelijkheid bij een specifieke vraag
               (KIK-V, Datastation: "Weet ik niet"), eveneens 0 punten
"""

INHOUD = {'answers': [['Aantoonbaar geregeld', 3],
             ['Grotendeels geregeld', 2],
             ['Beperkt geregeld', 1],
             ['Nee / onbekend', 0]],
 'cats': [[0, 39, 'Basis op orde brengen'],
          [40, 59, 'In ontwikkeling'],
          [60, 79, 'Goed op weg'],
          [80, 100, None]],
 'positioning': [['Readiness Check',
                  'Eerste indicatie op basis van uw zelfbeoordeling. Gratis, direct, zonder '
                  'gegevens achter te laten.'],
                 ['Volledig Readiness-rapport',
                  'Persoonlijke verdieping op basis van uw gegeven antwoorden: alle dimensies, '
                  'sterke punten, aandachtspunten en verbeterstappen.'],
                 ['Datagereedheidsscan / KIK-V-ondersteuning',
                  'Verdiepend onderzoek en advies op basis van de werkelijke situatie: uw data, '
                  'systemen en processen.']],
 'checks': {'data': {'title': 'Data Readiness Check',
                     'top': 'Datagereed',
                     'kind': 'Data',
                     'service': {'label': 'Bekijk de Datagereedheidsscan',
                                 'href': 'datagereedheidsscan.html'},
                     'service2': None,
                     'meaning': ['Uw antwoorden wijzen erop dat de basis voor datagedreven '
                                 'werken op meerdere fronten nog ontbreekt. Als dat beeld klopt, '
                                 'zullen nieuwe systemen, rapportages of uitwisselingen daarop '
                                 'vastlopen; de eerste winst zit dan in de fundamenten.',
                                 'Uw antwoorden wijzen erop dat er duidelijke eerste stappen '
                                 'zijn gezet, maar dat het nog niet structureel is. '
                                 'Verbeteringen lijken vooral aan personen en handwerk te '
                                 'hangen; het vastleggen van afspraken en processen is dan de '
                                 'logische volgende stap.',
                                 'Uw antwoorden wijzen erop dat uw organisatie goed op weg is. '
                                 'De basis lijkt te staan; de opgave zit in verdieping: '
                                 'aantoonbaar maken, standaardiseren en automatiseren waar dat '
                                 'nu nog handwerk is.',
                                 'Uw antwoorden wijzen op een datagereed niveau: basis, '
                                 'afspraken en techniek lijken op orde. De uitdaging is dan om '
                                 'dit vast te houden en te benutten voor nieuwe toepassingen '
                                 'zoals AI en uitwisseling.'],
                     'dims': [{'name': 'Databeschikbaarheid',
                               'q': ['Heeft uw organisatie inzicht in welke gegevens nodig zijn '
                                     'voor sturing, verantwoording en gegevensuitwisseling?',
                                     'Is bekend in welke bronsystemen deze gegevens worden '
                                     'vastgelegd?',
                                     'Kunnen benodigde gegevens zonder omvangrijke handmatige '
                                     'bewerkingen uit de bronsystemen beschikbaar worden '
                                     'gemaakt?'],
                               'advice': 'Begin met een gegevensinventarisatie: welke gegevens '
                                         'hebt u nodig voor sturing, verantwoording en '
                                         'uitwisseling, en in welk bronsysteem staan ze? Leg per '
                                         'gegeven vast waar het wordt vastgelegd en hoe het '
                                         'beschikbaar komt. Zolang dat overzicht ontbreekt, '
                                         'blijft elke rapportage of koppeling handwerk.',
                               'extra': None,
                               'low': 'Zolang niet vaststaat welke gegevens nodig zijn en waar '
                                      'ze staan, blijft elke informatievraag zoekwerk.',
                               'high': 'U weet welke gegevens ertoe doen, waar ze staan en hoe '
                                       'ze beschikbaar komen.',
                               'findings': ['Er is geen scherp beeld van welke gegevens nodig '
                                            'zijn voor sturing, verantwoording en uitwisseling; '
                                            'begin met een gegevensinventarisatie per doel.',
                                            'Het is niet (volledig) bekend in welke bronsystemen '
                                            'de benodigde gegevens worden vastgelegd; leg per '
                                            'gegeven het bronsysteem vast.',
                                            'Gegevens komen alleen met veel handwerk '
                                            'beschikbaar; kies de meest gevraagde gegevens en '
                                            'automatiseer de ontsluiting daarvan als eerste.'],
                               'strengths': ['De gegevensbehoefte voor sturing, verantwoording '
                                             'en uitwisseling is helder.',
                                             'Van de benodigde gegevens is het bronsysteem '
                                             'bekend.',
                                             'Gegevens komen zonder omvangrijk handwerk uit de '
                                             'bronsystemen beschikbaar.'],
                               'qa': [['Ja, volledig vastgelegd en actueel',
                                       'Ja, voor de meeste toepassingen bekend',
                                       'Deels en vooral vanuit de praktijk bekend',
                                       'Nee, dit is niet of nauwelijks in beeld'],
                                      ['Ja, volledig vastgelegd per gegeven',
                                       'Voor de meeste gegevens is dit bekend',
                                       'Voor een deel van de gegevens is dit bekend',
                                       'Nee, dit overzicht ontbreekt'],
                                      ['Ja, grotendeels automatisch en reproduceerbaar',
                                       'Ja, met beperkte handmatige bewerkingen',
                                       'Alleen met aanzienlijke handmatige bewerkingen',
                                       'Nee, of dit is onbekend']]},
                              {'name': 'Datakwaliteit',
                               'q': ['Wordt de kwaliteit van belangrijke gegevens periodiek en '
                                     'aantoonbaar gecontroleerd?',
                                     'Worden fouten, ontbrekende waarden en inconsistenties '
                                     'structureel geregistreerd en opgelost?',
                                     'Kan uw organisatie aantonen hoe de kwaliteit van '
                                     'belangrijke gegevens zich ontwikkelt?'],
                               'advice': 'Kies de vijf tot tien gegevens die er echt toe doen en '
                                         "spreek af wat 'goed' is: volledigheid, tijdigheid, "
                                         'juistheid. Meet die periodiek, registreer afwijkingen '
                                         'op één plek en maak zichtbaar of het beter wordt. '
                                         'Datakwaliteit verbetert pas als iemand het meet en er '
                                         'iets mee doet.',
                               'extra': None,
                               'low': 'Zonder periodieke controle en herstel blijft de '
                                      'betrouwbaarheid van rapportages een aanname.',
                               'high': 'Kwaliteit wordt gemeten, afwijkingen worden hersteld en '
                                       'de ontwikkeling is aantoonbaar.',
                               'findings': ['De kwaliteit van belangrijke gegevens wordt niet '
                                            'periodiek en aantoonbaar gecontroleerd; spreek per '
                                            'kerngegeven normen af en meet die vast.',
                                            'Fouten, ontbrekende waarden en inconsistenties '
                                            'worden niet structureel geregistreerd en opgelost; '
                                            'richt één plek in waar afwijkingen worden gelogd en '
                                            'opgevolgd.',
                                            'De ontwikkeling van datakwaliteit is niet '
                                            'aantoonbaar; leg meetmomenten vast zodat u '
                                            'verbetering kunt laten zien.'],
                               'strengths': ['Kwaliteit van belangrijke gegevens wordt periodiek '
                                             'en aantoonbaar gecontroleerd.',
                                             'Afwijkingen worden structureel geregistreerd en '
                                             'opgelost.',
                                             'De ontwikkeling van datakwaliteit is aantoonbaar.'],
                               'qa': [['Ja, structureel en aantoonbaar',
                                       'Ja, maar niet voor alle belangrijke gegevens',
                                       'Incidenteel of alleen bij problemen',
                                       'Nee, er vindt geen structurele controle plaats'],
                                      ['Ja, structureel geregistreerd, opgevolgd en opgelost',
                                       'Meestal, maar nog niet organisatiebreed',
                                       'Alleen incidenteel of bij acute problemen',
                                       'Nee, hiervoor bestaat geen vaste werkwijze'],
                                      ['Ja, de ontwikkeling wordt structureel gemeten',
                                       'Ja, voor een belangrijk deel van de gegevens',
                                       'Beperkt, vooral via losse metingen',
                                       'Nee, ontwikkeling is niet inzichtelijk']]},
                              {'name': 'Standaardisatie & betekenis',
                               'q': ['Zijn definities van belangrijke gegevens eenduidig '
                                     'vastgelegd en binnen de organisatie bekend?',
                                     'Worden waar mogelijk landelijke of sectorale standaarden '
                                     'gebruikt?',
                                     'Kan uw organisatie gegevens uit verschillende systemen '
                                     'eenduidig met elkaar verbinden en interpreteren?'],
                               'advice': 'Leg definities van kerngegevens vast in een '
                                         'begrippenlijst die zorg, administratie en ICT delen, '
                                         'en sluit waar het kan aan op landelijke standaarden '
                                         "zoals ZIB's. Zo voorkomt u dat 'cliënt', 'zorgmoment' "
                                         "of 'locatie' in elk systeem iets anders betekent en "
                                         'cijfers niet op elkaar aansluiten.',
                               'extra': None,
                               'low': 'Als definities per systeem verschillen, sluiten cijfers '
                                      "niet op elkaar aan en ontstaat discussie over 'welk getal "
                                      "klopt'.",
                               'high': 'Definities zijn eenduidig, standaarden worden gebruikt '
                                       'en gegevens uit verschillende systemen zijn te '
                                       'verbinden.',
                               'findings': ['Definities van belangrijke gegevens zijn niet '
                                            'eenduidig vastgelegd of niet breed bekend; stel een '
                                            'gedeelde begrippenlijst op voor zorg, administratie '
                                            'en ICT.',
                                            'Landelijke of sectorale standaarden worden nog '
                                            'beperkt gebruikt; toets per kerngegeven welke '
                                            "standaard (bijvoorbeeld ZIB's) van toepassing is.",
                                            'Gegevens uit verschillende systemen zijn niet '
                                            'eenduidig te verbinden; leg sleutels en definities '
                                            'vast waarop systemen op elkaar aansluiten.'],
                               'strengths': ['Definities van kerngegevens zijn eenduidig '
                                             'vastgelegd en bekend.',
                                             'Landelijke en sectorale standaarden worden waar '
                                             'mogelijk gebruikt.',
                                             'Gegevens uit verschillende systemen zijn eenduidig '
                                             'te verbinden en te interpreteren.'],
                               'qa': [['Ja, eenduidig vastgelegd en organisatiebreed gebruikt',
                                       'Grotendeels, met enkele verschillen of hiaten',
                                       'Alleen voor een beperkt aantal gegevens',
                                       'Nee, definities ontbreken of verschillen sterk'],
                                      ['Ja, structureel waar relevante standaarden bestaan',
                                       'Grotendeels, maar nog niet overal',
                                       'Alleen voor enkele toepassingen of gegevens',
                                       'Nee, of het gebruik ervan is onbekend'],
                                      ['Ja, structureel en op basis van vaste afspraken',
                                       'Ja, voor de meeste belangrijke gegevens',
                                       'Alleen met aanvullende handmatige interpretatie',
                                       'Nee, gegevens zijn niet eenduidig te verbinden of dit is '
                                       'onbekend']]},
                              {'name': 'Governance & eigenaarschap',
                               'q': ['Is voor belangrijke gegevens duidelijk wie '
                                     'verantwoordelijk is voor kwaliteit en beschikbaarheid?',
                                     'Zijn afspraken gemaakt over wie fouten in gegevens moet '
                                     'onderzoeken en herstellen?',
                                     'Zijn privacy, informatiebeveiliging en toegangsrechten '
                                     'onderdeel van het dataproces?'],
                               'advice': 'Benoem per kerngegeven een eigenaar met mandaat en '
                                         'maak afspraken over wie fouten onderzoekt en herstelt. '
                                         'Neem privacy, beveiliging en toegangsrechten op in '
                                         'datzelfde proces in plaats van als losse checklist. '
                                         'Een korte Data Governance Sprint zet dit in enkele '
                                         'weken werkend neer.',
                               'extra': None,
                               'low': 'Zonder eigenaarschap blijft datakwaliteit ieders en '
                                      'daarmee niemands verantwoordelijkheid.',
                               'high': 'Eigenaarschap, herstelafspraken en privacy-, '
                                       'beveiligings- en toegangsregels zijn onderdeel van het '
                                       'dataproces.',
                               'findings': ['Voor belangrijke gegevens is niet duidelijk wie '
                                            'verantwoordelijk is voor kwaliteit en '
                                            'beschikbaarheid; benoem per kerngegeven een '
                                            'eigenaar met mandaat.',
                                            'Er zijn geen afspraken over wie fouten onderzoekt '
                                            'en herstelt; leg een eenvoudige herstelroute vast '
                                            '(melden, beoordelen, herstellen, terugkoppelen).',
                                            'Privacy, informatiebeveiliging en toegangsrechten '
                                            'zijn geen vast onderdeel van het dataproces; neem '
                                            'ze op in dezelfde afspraken in plaats van als losse '
                                            'checklist.'],
                               'strengths': ['Eigenaarschap van kerngegevens is belegd.',
                                             'Er zijn afspraken over het onderzoeken en '
                                             'herstellen van fouten.',
                                             'Privacy, beveiliging en toegangsrechten zijn '
                                             'onderdeel van het dataproces.'],
                               'qa': [['Ja, eigenaarschap en verantwoordelijkheden zijn '
                                       'vastgelegd',
                                       'Grotendeels, maar niet voor alle gegevens',
                                       'Informeel of slechts voor enkele gegevens',
                                       'Nee, verantwoordelijkheden zijn niet duidelijk'],
                                      ['Ja, rollen en werkwijze zijn duidelijk vastgelegd',
                                       'Grotendeels, maar niet in alle situaties',
                                       'Er zijn vooral informele afspraken',
                                       'Nee, hierover zijn geen duidelijke afspraken'],
                                      ['Ja, structureel en aantoonbaar ingebed',
                                       'Grotendeels, maar niet in alle processen',
                                       'Alleen op onderdelen of achteraf',
                                       'Nee, deze zijn niet structureel onderdeel van het '
                                       'dataproces']]},
                              {'name': 'Techniek & hergebruik',
                               'q': ['Kunnen gegevens geautomatiseerd worden ontsloten voor '
                                     'andere toepassingen of partijen?',
                                     'Kan dezelfde brondata worden hergebruikt voor meerdere '
                                     'informatievragen zonder telkens nieuwe handmatige '
                                     'bestanden te maken?',
                                     'Is uw technische omgeving voorbereid op verdere '
                                     'standaardisatie en elektronische gegevensuitwisseling?'],
                               'advice': 'Breng in kaart welke uitvragen nu handmatig uit '
                                         'exports worden samengesteld en richt voor die gegevens '
                                         'één geautomatiseerde ontsluiting in die meerdere '
                                         'vragen tegelijk bedient. Toets daarbij of uw '
                                         'leveranciers koppelvlakken volgens de landelijke '
                                         'standaarden ondersteunen, zodat u niet voor elke '
                                         'nieuwe verplichting opnieuw begint.',
                               'extra': None,
                               'low': 'Zolang elke informatievraag een nieuw handmatig bestand '
                                      'betekent, schaalt het niet en groeit de foutkans.',
                               'high': 'Gegevens worden geautomatiseerd ontsloten en '
                                       'hergebruikt; de omgeving is klaar voor verdere '
                                       'standaardisatie.',
                               'findings': ['Gegevens kunnen niet geautomatiseerd worden '
                                            'ontsloten voor andere toepassingen of partijen; '
                                            'richt voor de meest gevraagde gegevens één '
                                            'geautomatiseerde ontsluiting in.',
                                            'Dezelfde brondata wordt telkens opnieuw handmatig '
                                            'samengesteld; breng de terugkerende uitvragen in '
                                            'kaart en bedien ze vanuit één bron.',
                                            'De technische omgeving is niet voorbereid op '
                                            'verdere standaardisatie en elektronische '
                                            'uitwisseling; toets met leveranciers welke '
                                            'koppelvlakken volgens landelijke standaarden '
                                            'beschikbaar zijn.'],
                               'strengths': ['Gegevens worden geautomatiseerd ontsloten.',
                                             'Brondata wordt hergebruikt voor meerdere '
                                             'informatievragen.',
                                             'De technische omgeving is voorbereid op '
                                             'standaardisatie en elektronische uitwisseling.'],
                               'qa': [['Ja, via gestandaardiseerde en geautomatiseerde '
                                       'koppelingen',
                                       'Grotendeels, maar niet voor alle gegevens',
                                       'Beperkt, met veel maatwerk of handwerk',
                                       'Nee, geautomatiseerde ontsluiting is niet mogelijk of '
                                       'onbekend'],
                                      ['Ja, brondata wordt structureel meervoudig gebruikt',
                                       'Grotendeels, maar soms zijn aparte bewerkingen nodig',
                                       'Beperkt, vaak worden nieuwe bestanden gemaakt',
                                       'Nee, informatievragen worden afzonderlijk opgebouwd'],
                                      ['Ja, architectuur en techniek zijn hierop ingericht',
                                       'Grotendeels, enkele aanpassingen zijn nog nodig',
                                       'Beperkt, aanzienlijke aanpassingen zijn nodig',
                                       'Nee, de huidige omgeving is hier niet op voorbereid of '
                                       'dit is onbekend']]}]},
            'kikv': {'title': 'KIK-V Readiness Check',
                     'top': 'KIK-V-gereed',
                     'kind': 'KIK-V',
                     'service': {'label': 'Onderzoek uw implementatiegereedheid',
                                 'href': 'implementatiegereedheid.html'},
                     'service2': {'label': 'Expertise gegevensuitwisseling',
                                  'href': 'expertise.html'},
                     'meaning': ['Uw antwoorden wijzen erop dat de voorbereiding op KIK-V nog '
                                 'aan het begin staat. Als dat beeld klopt, zou u bij een '
                                 'uitvraag nu vastlopen op ontbrekende gegevens, definities of '
                                 'techniek; beginnen bij de gegevensset en het eigenaarschap '
                                 'ligt dan voor de hand.',
                                 'Uw antwoorden wijzen erop dat de voorbereiding op KIK-V in '
                                 'ontwikkeling is. Onderdelen zijn opgepakt, maar de keten van '
                                 'bron tot uitwisseling lijkt nog niet sluitend; het expliciet '
                                 'maken en plannen van de open schakels is de volgende stap.',
                                 'Uw antwoorden wijzen erop dat u goed op weg bent met KIK-V. De '
                                 'meeste schakels lijken te staan; de opgave is de resterende '
                                 'schakels sluiten en de kwaliteit aantoonbaar maken vóór de '
                                 'eerste uitwisseling.',
                                 'Uw antwoorden wijzen op een KIK-V-gereed niveau: gegevens, '
                                 'definities, organisatie en techniek lijken op elkaar aan te '
                                 'sluiten. Richt u dan op het borgen en op hergebruik voor '
                                 'andere informatievragen.'],
                     'dims': [{'name': 'Gegevensbeschikbaarheid',
                               'q': ['Is binnen uw organisatie bekend welke gegevens voor KIK-V '
                                     'beschikbaar moeten zijn?',
                                     'Is bekend uit welke bronsystemen deze gegevens afkomstig '
                                     'zijn?',
                                     'Kan de organisatie de benodigde gegevens grotendeels uit '
                                     'bestaande registraties ontsluiten?'],
                               'advice': 'Zet de KIK-V-gegevensset naast uw eigen registraties '
                                         'en markeer per gegeven: aanwezig, aanwezig maar in een '
                                         'ander systeem, of ontbreekt. Dat overzicht is de basis '
                                         'voor alle vervolgstappen en voorkomt dat u pas bij de '
                                         'eerste uitvraag ontdekt wat er mist.',
                               'extra': None,
                               'low': 'Zonder een volledig beeld van de KIK-V-gegevensset en de '
                                      'bronnen ontdekt u pas bij de eerste uitvraag wat '
                                      'ontbreekt.',
                               'high': 'De KIK-V-gegevensset is in beeld, de bronnen zijn bekend '
                                       'en de gegevens zijn grotendeels te ontsluiten.',
                               'findings': ['Het is niet volledig bekend welke gegevens voor '
                                            'KIK-V beschikbaar moeten zijn; leg de '
                                            'KIK-V-gegevensset naast uw eigen registraties.',
                                            'De bronsystemen van de KIK-V-gegevens zijn niet '
                                            '(allemaal) bekend; markeer per gegeven waar het '
                                            'vandaan komt.',
                                            'De benodigde gegevens zijn niet grotendeels uit '
                                            'bestaande registraties te ontsluiten; bepaal welke '
                                            'gegevens nu ontbreken of alleen via handwerk '
                                            'beschikbaar komen.'],
                               'strengths': ['Bekend is welke gegevens voor KIK-V beschikbaar '
                                             'moeten zijn.',
                                             'De bronsystemen van de KIK-V-gegevens zijn bekend.',
                                             'De benodigde gegevens zijn grotendeels uit '
                                             'bestaande registraties te ontsluiten.']},
                              {'name': 'Datakwaliteit',
                               'q': ['Is onderzocht of de benodigde KIK-V-gegevens volledig en '
                                     'correct worden geregistreerd?',
                                     'Worden afwijkingen in gegevens structureel opgespoord en '
                                     'hersteld?',
                                     'Kan de organisatie de kwaliteit van de voor KIK-V '
                                     'gebruikte gegevens aantoonbaar maken?'],
                               'advice': 'Toets de KIK-V-gegevens op volledigheid en juistheid '
                                         'aan de bron, te beginnen bij de indicatoren die het '
                                         'meest gevoelig zijn voor registratiefouten. Leg vast '
                                         'hoe afwijkingen worden opgespoord en hersteld, zodat u '
                                         'bij een uitvraag kunt laten zien waar de cijfers op '
                                         'gebaseerd zijn.',
                               'extra': None,
                               'low': 'Onderzochte en herstelde brondata is de voorwaarde om '
                                      'cijfers bij een uitvraag te kunnen verantwoorden.',
                               'high': 'De KIK-V-gegevens zijn getoetst, afwijkingen worden '
                                       'hersteld en de kwaliteit is aantoonbaar.',
                               'findings': ['Er is niet onderzocht of de KIK-V-gegevens volledig '
                                            'en correct worden geregistreerd; toets ze aan de '
                                            'bron, te beginnen bij de meest foutgevoelige '
                                            'indicatoren.',
                                            'Afwijkingen in gegevens worden niet structureel '
                                            'opgespoord en hersteld; leg vast hoe afwijkingen '
                                            'worden gesignaleerd en wie ze herstelt.',
                                            'De kwaliteit van de KIK-V-gegevens is niet '
                                            'aantoonbaar; leg meetresultaten vast zodat u bij '
                                            'een uitvraag kunt laten zien waarop de cijfers '
                                            'rusten.'],
                               'strengths': ['Onderzocht is of de KIK-V-gegevens volledig en '
                                             'correct worden geregistreerd.',
                                             'Afwijkingen worden structureel opgespoord en '
                                             'hersteld.',
                                             'De kwaliteit van de KIK-V-gegevens is '
                                             'aantoonbaar.']},
                              {'name': 'Betekenis & mapping',
                               'q': ['Is duidelijk hoe gegevens uit de eigen systemen aansluiten '
                                     'op de definities binnen KIK-V?',
                                     'Zijn noodzakelijke mappings tussen eigen gegevens en '
                                     'KIK-V-definities beschikbaar of in ontwikkeling?',
                                     'Is binnen de organisatie voldoende kennis aanwezig om '
                                     'verschillen in definities te herkennen en op te lossen?'],
                               'advice': 'Maak per KIK-V-definitie expliciet welk eigen gegeven '
                                         'erachter zit en waar de betekenis afwijkt. Werk die '
                                         'mappings uit met iemand die zowel de zorgregistratie '
                                         'als de KIK-V-afsprakenset kent; definitieverschillen '
                                         'zijn de meest voorkomende oorzaak van onjuiste cijfers '
                                         'bij een uitvraag.',
                               'extra': None,
                               'low': 'Definitieverschillen tussen eigen registraties en KIK-V '
                                      'zijn de meest voorkomende oorzaak van onjuiste cijfers.',
                               'high': 'De aansluiting op de KIK-V-definities is helder, '
                                       'mappings zijn beschikbaar en de kennis is in huis.',
                               'findings': ['Het is niet duidelijk hoe eigen gegevens aansluiten '
                                            'op de KIK-V-definities; maak per definitie '
                                            'expliciet welk eigen gegeven erachter zit.',
                                            'Noodzakelijke mappings tussen eigen gegevens en '
                                            'KIK-V-definities ontbreken of zijn nog niet '
                                            'gestart; begin met de indicatoren die het eerst '
                                            'worden uitgevraagd.',
                                            'Er is onvoldoende kennis om definitieverschillen te '
                                            'herkennen en op te lossen; koppel iemand met kennis '
                                            'van de zorgregistratie aan iemand die de '
                                            'afsprakenset kent.'],
                               'strengths': ['De aansluiting van eigen gegevens op de '
                                             'KIK-V-definities is duidelijk.',
                                             'Mappings tussen eigen gegevens en KIK-V-definities '
                                             'zijn beschikbaar of in ontwikkeling.',
                                             'Er is voldoende kennis om definitieverschillen te '
                                             'herkennen en op te lossen.']},
                              {'name': 'Organisatie & governance',
                               'q': ['Is duidelijk wie binnen de organisatie verantwoordelijk is '
                                     'voor de KIK-V-implementatie?',
                                     'Zijn verantwoordelijkheden voor brondata, datakwaliteit en '
                                     'technische ontsluiting belegd?',
                                     'Werken zorginhoudelijke, administratieve en '
                                     'ICT-disciplines samen bij gegevensvraagstukken?'],
                               'advice': 'Benoem één eigenaar voor de KIK-V-implementatie en '
                                         'beleg brondata, datakwaliteit en technische '
                                         'ontsluiting bij herkenbare rollen. Breng zorg, '
                                         'administratie en ICT periodiek samen rond de '
                                         'gegevensvragen; KIK-V loopt vast waar die drie langs '
                                         'elkaar heen werken.',
                               'extra': None,
                               'low': 'KIK-V loopt vast waar zorg, administratie en ICT langs '
                                      'elkaar heen werken en niemand eigenaar is.',
                               'high': 'Eigenaarschap van de implementatie is belegd en de '
                                       'disciplines werken samen aan gegevensvraagstukken.',
                               'findings': ['Het is niet duidelijk wie verantwoordelijk is voor '
                                            'de KIK-V-implementatie; benoem één eigenaar met '
                                            'mandaat.',
                                            'Verantwoordelijkheden voor brondata, datakwaliteit '
                                            'en technische ontsluiting zijn niet belegd; verdeel '
                                            'ze over herkenbare rollen.',
                                            'Zorginhoudelijke, administratieve en '
                                            'ICT-disciplines werken niet samen aan '
                                            'gegevensvraagstukken; organiseer een vast, kort '
                                            'overleg rond de KIK-V-gegevens.'],
                               'strengths': ['Eigenaarschap van de KIK-V-implementatie is '
                                             'duidelijk.',
                                             'Verantwoordelijkheden voor brondata, datakwaliteit '
                                             'en ontsluiting zijn belegd.',
                                             'Zorg, administratie en ICT werken samen aan '
                                             'gegevensvraagstukken.']},
                              {'name': 'Techniek & gegevensuitwisseling',
                               'q': ['Is er een Datastation beschikbaar of is een '
                                     'keuze/implementatie daarvan gestart?',
                                     'Kan de organisatie gegevens technisch aanbieden conform de '
                                     'afgesproken KIK-V-uitwisseling?',
                                     'Kan de organisatie de gegevens vóór uitwisseling technisch '
                                     'en inhoudelijk valideren?'],
                               'advice': 'Start de keuze voor een Datastation als die nog niet '
                                         'gemaakt is, en spreek met uw leveranciers af hoe '
                                         'gegevens conform de KIK-V-uitwisseling worden '
                                         'aangeboden. Richt daarnaast een validatiestap in vóór '
                                         'uitwisseling, zodat u zelf ziet wat er naar buiten '
                                         'gaat voordat een uitvragende partij het ziet.',
                               'extra': {'idx': 0, 'label': 'Weet ik niet'},
                               'low': 'Zonder Datastation en validatiestap kunt u gegevens niet '
                                      'conform de afspraken aanbieden, hoe goed de data ook is.',
                               'high': 'Het Datastation is beschikbaar of in gang, gegevens '
                                       'kunnen conform de uitwisseling worden aangeboden en '
                                       'worden vooraf gevalideerd.',
                               'findings': ['Er is nog geen Datastation beschikbaar en de keuze '
                                            'of implementatie is niet gestart (of onbekend); '
                                            'start de oriëntatie en betrek de ECD-leverancier.',
                                            'Gegevens kunnen nog niet technisch worden '
                                            'aangeboden conform de KIK-V-uitwisseling; spreek '
                                            'met leveranciers af hoe en wanneer dit wordt '
                                            'ondersteund.',
                                            'Gegevens worden vóór uitwisseling niet technisch en '
                                            'inhoudelijk gevalideerd; richt een validatiestap in '
                                            'zodat u zelf ziet wat er naar buiten gaat.'],
                               'strengths': ['Een Datastation is beschikbaar of de '
                                             'keuze/implementatie is gestart.',
                                             'Gegevens kunnen technisch conform de '
                                             'KIK-V-uitwisseling worden aangeboden.',
                                             'Gegevens worden vóór uitwisseling technisch en '
                                             'inhoudelijk gevalideerd.']}]}}}
