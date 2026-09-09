from django.db import migrations, models

EUROPEAN_COUNTRIES = {
    'england', 'spain', 'italy', 'germany', 'france', 'portugal', 'netherlands',
    'belgium', 'turkey', 'scotland', 'norway', 'sweden', 'denmark', 'poland',
    'greece', 'switzerland', 'austria', 'russia', 'ukraine', 'croatia', 'serbia',
    'czech-republic', 'czech republic', 'romania', 'hungary', 'bulgaria', 'cyprus',
    'israel', 'slovakia', 'slovenia', 'finland', 'ireland', 'wales', 'northern-ireland',
    'northern ireland', 'iceland', 'bosnia', 'albania', 'belarus', 'armenia',
    'azerbaijan', 'georgia', 'kazakhstan', 'moldova', 'malta', 'luxembourg',
    'estonia', 'latvia', 'lithuania', 'faroe-islands', 'faroe islands', 'gibraltar',
    'andorra', 'san-marino', 'san marino', 'kosovo', 'liechtenstein', 'montenegro',
    'north-macedonia', 'north macedonia'
}

SOUTH_AMERICAN_COUNTRIES = {
    'brazil', 'argentina', 'colombia', 'chile', 'uruguay', 'ecuador',
    'peru', 'paraguay', 'bolivia', 'venezuela', 'guyana', 'suriname'
}

NORTH_CENTRAL_AMERICAN_COUNTRIES = {
    'usa', 'united-states', 'mexico', 'canada', 'costa-rica', 'costa rica',
    'honduras', 'jamaica', 'panama', 'guatemala', 'el-salvador', 'el salvador',
    'trinidad-and-tobago', 'trinidad and tobago', 'haiti', 'cuba', 'curacao',
    'curaçao', 'dominican-republic', 'dominican republic', 'nicaragua', 'martinique',
    'guadeloupe', 'barbados', 'bermuda', 'belize', 'suriname', 'puerto-rico'
}

ASIAN_COUNTRIES = {
    'saudi-arabia', 'saudi arabia', 'japan', 'south-korea', 'south korea',
    'china', 'australia', 'uae', 'united-arab-emirates', 'qatar', 'iran',
    'iraq', 'india', 'thailand', 'indonesia', 'uzbekistan', 'vietnam',
    'jordan', 'bahrain', 'kuwait', 'oman', 'lebanon', 'syria', 'palestine',
    'singapore', 'malaysia', 'philippines', 'myanmar', 'hong-kong', 'hong kong',
    'tajikistan', 'turkmenistan', 'kyrgyzstan'
}

AFRICAN_COUNTRIES = {
    'egypt', 'morocco', 'algeria', 'tunisia', 'south-africa', 'south africa',
    'nigeria', 'ghana', 'senegal', 'ivory-coast', 'ivory coast', 'cote-d-ivoire',
    'cameroon', 'angola', 'congo', 'congo dr', 'dr congo', 'kenya', 'uganda',
    'tanzania', 'zambia', 'zimbabwe', 'mali', 'burkina-faso', 'burkina faso',
    'guinea', 'benin', 'togo', 'gambia', 'sudan', 'ethiopia', 'rwanda',
    'libya', 'mauritania', 'seychelles', 'madagascar', 'mozambique', 'botswana',
    'namibia', 'malawi', 'eswatini', 'lesotho', 'cape-verde', 'sierra-leone'
}

OCEANIAN_COUNTRIES = {
    'new-zealand', 'new zealand', 'fiji', 'papua-new-guinea', 'papua new guinea',
    'solomon-islands', 'tahiti', 'vanuatu', 'samoa', 'tonga', 'new-caledonia'
}

KNOWN_TOURNAMENTS = {
    # Europe (UEFA)
    2: 'Europe',    # UEFA Champions League
    3: 'Europe',    # UEFA Europa League
    848: 'Europe',  # UEFA Europa Conference League
    5: 'Europe',    # UEFA Nations League
    525: 'Europe',  # UEFA Super Cup / UEFA Women CL
    4: 'Europe',    # UEFA Euro
    849: 'Europe',  # UEFA Youth League
    765: 'Europe',  # UEFA Women's Champions League
    823: 'Europe',  # Nasjonal U19 Champions League (Norway)
    
    # Africa (CAF)
    12: 'Africa',   # CAF Champions League
    20: 'Africa',   # CAF Confederation Cup
    6: 'Africa',    # Africa Cup of Nations
    1164: 'Africa', # CAF Women's Champions League
    
    # Asia (AFC)
    17: 'Asia',     # AFC Champions League Elite
    18: 'Asia',     # AFC Champions League Two
    7: 'Asia',      # AFC Asian Cup
    1140: 'Asia',   # AFC Women's Champions League
    1162: 'Asia',   # AGCFF Gulf Champions League
    
    # South America (CONMEBOL)
    11: 'South America',  # Copa Sudamericana
    13: 'South America',  # Copa Libertadores
    14: 'South America',  # Recopa Sudamericana
    9: 'South America',   # Copa America
    
    # North & Central America (CONCACAF)
    16: 'North & Central America',  # CONCACAF Champions Cup / League
    22: 'North & Central America',  # CONCACAF Gold Cup
    1058: 'North & Central America', # Leagues Cup
    856: 'North & Central America', # CONCACAF Caribbean Club Championship
    
    # Oceania (OFC)
    27: 'Oceania',  # OFC Champions League
    24: 'Oceania',  # OFC Nations Cup
    25: 'Oceania',
    1045: 'Oceania',
    
    # World (FIFA)
    1: 'World',     # World Cup
    15: 'World',    # FIFA Club World Cup
    10: 'World',    # Friendlies
    667: 'World',   # Friendlies Women
}


def resolve_region(league_id, league_name, country_name):
    if league_id in KNOWN_TOURNAMENTS:
        return KNOWN_TOURNAMENTS[league_id]

    lname = (league_name or '').lower()
    cname = (country_name or '').lower().strip()

    # Name-based continental cues
    if any(k in lname for k in ['uefa', 'euro ']):
        return 'Europe'
    if any(k in lname for k in ['caf ', 'africa']):
        return 'Africa'
    if any(k in lname for k in ['afc ', 'asian ']):
        return 'Asia'
    if any(k in lname for k in ['conmebol', 'libertadores', 'sudamericana', 'copa américa', 'copa america']):
        return 'South America'
    if any(k in lname for k in ['concacaf', 'leagues cup']):
        return 'North & Central America'
    if 'ofc ' in lname:
        return 'Oceania'
    if any(k in lname for k in ['fifa', 'world cup', 'olympics']):
        return 'World'

    # Country-based continental classification
    if cname in EUROPEAN_COUNTRIES:
        return 'Europe'
    if cname in SOUTH_AMERICAN_COUNTRIES:
        return 'South America'
    if cname in NORTH_CENTRAL_AMERICAN_COUNTRIES:
        return 'North & Central America'
    if cname in ASIAN_COUNTRIES:
        return 'Asia'
    if cname in AFRICAN_COUNTRIES:
        return 'Africa'
    if cname in OCEANIAN_COUNTRIES:
        return 'Oceania'

    if cname in ('world', 'international'):
        return 'World'

    return 'World'


def populate_league_regions(apps, schema_editor):
    League = apps.get_model('sports', 'League')
    for league in League.objects.select_related('country').all():
        country_name = league.country.name if league.country else ''
        league.region = resolve_region(league.id, league.name, country_name)
        league.save(update_fields=['region'])


class Migration(migrations.Migration):

    dependencies = [
        ('sports', '0010_fixture_extra'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='league',
                    name='region',
                    field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE sports_league ADD COLUMN IF NOT EXISTS region varchar(100);",
                    reverse_sql="ALTER TABLE sports_league DROP COLUMN IF EXISTS region;",
                ),
            ],
        ),
        migrations.RunPython(populate_league_regions, migrations.RunPython.noop),
    ]
