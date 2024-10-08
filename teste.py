import io
import json
from pymongo import MongoClient
from datetime import datetime, timedelta
from pathlib import Path
from openai import OpenAI
import requests
from bson import ObjectId
import re
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

import config
DEV = config.DEV_MODE
GPT_API_KEY = config.GPT_API_KEY

def add_date():
    collection = access_mongodb("political", "chats")

    base_date = datetime.strptime("2024-07-23", "%Y-%m-%d")
    for entry in collection.find():
        last_message = entry.get("last_message_date", None)
        messages = entry.get("messages", [])
        messages_data = []
        find_last_msg_date = []
        data_changed = False

        for message in messages:
            copy_msg = message.copy()
            if message.get("date", None) is None:
                copy_msg["date"] = base_date
                data_changed = True

            find_last_msg_date.append(copy_msg["date"])   
            type = copy_msg["type"]
            if type == "video" or type == "image":
                continue

            messages_data.append(copy_msg)
        
        last_msg_date = max(find_last_msg_date)

        if data_changed:
            data_set = {"messages": messages_data}

            if last_message is None:
                data_set["last_message_date"] = last_msg_date

            collection.update_one({"_id": entry["_id"]}, {"$set": data_set})

def transcript_audio():
    collection = access_mongodb("political", "chats")
    client = OpenAI(api_key=GPT_API_KEY)

    for entry in collection.find():
        messages = entry.get("messages", [])
        has_audio = False

        for message in messages:
            if message.get("type") == "audio":
                if message.get("transcript", None) is not None:
                    continue

                audio_file_path = message.get("value")

                try:
                    transcript = client.audio.transcriptions.create(
                        file=("audio", io.BytesIO(requests.get(audio_file_path, stream=True).content), "audio/ogg"),
                        model="whisper-1",

                    )
                    text = transcript.text
                    message["transcript"] = text
                
                    has_audio = True

                except Exception as e:
                    print(e)

        if has_audio:
            collection.update_one({"_id": entry["_id"]}, {"$set": {"messages": messages}})

def adiciona_runzinho():
    collection = access_mongodb("political", "affiliates_webhook")

    json_path = Path("C:\\Users\\thiag\\Downloads\\political.affiliates_webhook.json")

    with open(json_path, 'r', encoding='utf-8') as json_file:
        contacts = json.load(json_file)

    for contact in contacts:
        contact_phone = contact.get("clientNumber", None)

        if contact_phone is None or collection.count_documents({"clientNumber": contact_phone}) == 0:
            continue

        collection.update_one({"clientNumber": contact_phone}, {"$set": {"run": True}})

def change_msg():
    collection = access_mongodb("political", "affiliates")

    for entry in collection.find():
        messages = entry.get("first_messages", {}).get("messages", [])

        if len(messages) == 3:
            updated_messages = messages[:2]

            collection.update_one({"_id": entry["_id"]}, {"$set": {"first_messages.messages": updated_messages}})
    
def merge_msg():
    collection = access_mongodb("political", "chats")
    processed_pairs = set()

    for index, entry in enumerate(collection.find()):
        client_phone = entry.get("phone", "")
        affiliate_id = entry.get("affiliate_id", "")

        if client_phone == "" or (client_phone, affiliate_id) in processed_pairs:
            continue

        processed_pairs.add((client_phone, affiliate_id))
        
        documents = list(collection.find({"phone": client_phone, "affiliate_id": affiliate_id}))

        if len(documents) <= 1:
            continue

        merged_messages = []

        for document in documents:
            merged_messages.extend(document.get("messages", []))

        collection.update_one({"_id": documents[0]["_id"]}, {"$set": {"messages": merged_messages}})           
        print(f"{index} - cliente {client_phone} atualizado")

        for document in documents[1:]:
            collection.delete_one({"_id": document["_id"]})

            print(f"cliente {document['_id']} removido")

async def async_merge_msg():
    collection = await async_access_mongodb("political", "chats")
    processed_pairs = set()
    index = 8000

    async for entry in collection.find().skip(index):
        client_phone = entry.get("phone", "")
        affiliate_id = entry.get("affiliate_id", "")

        if client_phone == "" or (client_phone, affiliate_id) in processed_pairs:
            print(f"{index} - cliente {client_phone} ignorado")
            index += 1
            continue

        processed_pairs.add((client_phone, affiliate_id))
        
        documents = await collection.find({"phone": client_phone, "affiliate_id": affiliate_id}).to_list(length=None)

        if len(documents) <= 1:
            print(f"{index} - cliente {client_phone} não repetido")
            index += 1
            continue

        merged_messages = []

        for document in documents:
            merged_messages.extend(document.get("messages", []))

        await collection.update_one({"_id": documents[0]["_id"]}, {"$set": {"messages": merged_messages}})           
        print(f"{index} - cliente {client_phone} atualizado")

        for document in documents[1:]:
            await collection.delete_one({"_id": document["_id"]})
            print(f"cliente {document['_id']} removido")

        index += 1

async def update_group_msg():
    collection = await async_access_mongodb("political", "affiliates")

    new_text = 'Olá! Agradecemos imensamente pelo interesse no Video AI!\n\nEstamos enfrentando uma alta demanda com 3.560 vereadores na fila. Mas não se preocupe! Aumentamos nossa equipe e estaremos produzindo todo o material demonstrativo neste sábado e domingo.\n\nPara manter todos informados sobre o andamento e a produção dos materiais demonstrativos, criamos uma comunidade exclusiva. Nela, nossa equipe enviará todas as atualizações importantes.\n\nAcesse o link abaixo e clique em "*ENTRAR NO GRUPO*" para se manter informado. Lembrando que apenas nossa equipe poderá enviar mensagens.\n\n👇👇👇\nhttps://chat.whatsapp.com/HknDUr4C1JMJeX3rbrg5Z0'

    async for document in collection.find({}):
        first_messages = document.get("first_messages", {})
        messages = first_messages.get("messages", [])

        for message in messages:
            if message["type"] != "text":
                continue
            message["text"] = new_text

        await collection.update_one({"_id": document["_id"]}, {"$set": {"first_messages.messages": messages}})

async def remove_old_messages():
    collection = await async_access_mongodb("political", "chats")
    message_limit = 100
    for document in await collection.find({}).to_list(length=None):
        messages = document.get("messages", [])

        if len(messages) > message_limit:
            updated_messages = messages[-message_limit:]
            await collection.update_one({"_id": document["_id"]}, {"$set": {"messages": updated_messages}})
            print(f"cliente {document['_id']} atualizado")

def access_mongodb(db_name, collection_name):
    uri = "mongodb://videoaimidias:vxZE5CZ8Z0ba3yQsKbMMAYRsGB7L36g3axA1VdJa3MWhDUxrBu@137.184.45.31:27017/videoai" if not DEV else "mongodb://localhost:27017/"
    client = MongoClient(uri)
    db = client[db_name]
    
    return db[collection_name]

async def async_access_mongodb(db_name, collection_name):
    uri = "mongodb://videoaimidias:vxZE5CZ8Z0ba3yQsKbMMAYRsGB7L36g3axA1VdJa3MWhDUxrBu@137.184.45.31:27017/videoai" if not DEV else "mongodb://localhost:27017/"
    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    collection = db[collection_name]
    return collection

def analyse_messages():
    didnt_send_link_json = Path("C:\\Users\\thiag\\Downloads\\didnt_send_link.json")
    wrong_link_json = Path("C:\\Users\\thiag\\Downloads\\wrong_link.json")

    with open(didnt_send_link_json, 'r', encoding='utf-8') as json_file:
        didnt_send_link = json.load(json_file)

    with open(wrong_link_json, 'r', encoding='utf-8') as json_file:
        wrong_link = json.load(json_file)

    phones_didnt_send = {entry["phone"] for entry in didnt_send_link}
    new_wrong_link = {entry["phone"]: entry["affiliate_id"] for entry in wrong_link if entry["phone"] not in phones_didnt_send}
    new_didnt_send = {entry["phone"]: entry["affiliate_id"] for entry in didnt_send_link}

    with open("new_wrong_link.json", 'w', encoding='utf-8') as json_file:
        json.dump(new_wrong_link, json_file, indent=4)
    
    with open("new_didnt_send.json", 'w', encoding='utf-8') as json_file:
        json.dump(new_didnt_send, json_file, indent=4)

async def separate_first_messages():
    affiliates_collection = await async_access_mongodb("political", "affiliates")
    new_affiliates_collection = await async_access_mongodb("political", "affiliates_first_messages")

    new_collection_data = []
    total_phones = 0
    async for affiliate in affiliates_collection.find({}):
        affiliate_id = affiliate.get("_id")
        first_message_already_sent = affiliate.get("first_message_already_sent", [])
        total_phones += len(first_message_already_sent)
        print(f"telefones no afiliado {affiliate_id}: {len(first_message_already_sent)}")
        print(f"total de telefones: {total_phones}")
        for phone in first_message_already_sent:
            new_collection_data.append({
                "affiliate_id": affiliate_id,
                "phone": phone
            })
        print(f"{affiliate_id} finalizado")

    await new_affiliates_collection.insert_many(new_collection_data)

phones = [
"5516996311641",
"558588680101",
"556496644763",
"558594499566",
"5511948462925",
"553588896391",
"556285762473",
"559187424821",
"553198056213",
"554888242873",
"553192786625",
"5518996539462",
"5516991960187",
"558498958059",
"554396048466",
"553799991559",
"553287024485",
"559381011213",
"558596218568",
"559184735145",
"556692349670",
"5517991384636",
"554391083367",
"555599836814",
"5515996995571",
"5528992557950",
"557399690222",
"5511969051872",
"556194372133",
"558196939274",
"556599655290",
"559291964095",
"558585434929",
"556684582061",
"557996461300",
"5519997113111",
"558192616675",
"5511987182011",
"555182827914",
"5513988543196",
"558192345350",
"557788882632",
"558496032344",
"5511958479960",
"558393730205",
"559492962520",
"558591838109",
"557381288592",
"553285126662",
"556798961834",
"553287100717",
"558193406306",
"5511975192012",
"559185987583",
"558791254619",
"5518997110671",
"558592555424",
"553188184066",
"556696120094",
"5511985461077",
"553491185343",
"5518997525437",
"558791673132",
"5519999720009",
"558592097308",
"553388466509",
"557381601075",
"5519988015117",
"555599787919",
"557391235017",
"556499940151",
"554191152209",
"557591679103",
"559781035289",
"557391122700",
"555491310840",
"557799368711",
"559988197441",
"558296095655",
"556399823787",
"5513981369765",
"559981766441",
"5511949667646",
"558499592032",
"553588176806",
"553499390050",
"559491333107",
"5518998202089",
"559899706997",
"556294047518",
"5513981736058",
"558896040185",
"558188224721",
"556384813032",
"556499378861",
"557399953999",
"553499960205",
"553899133563",
"557981486037",
"559981860711",
"554299176935",
"553384444524",
"558199647913",
"554299326057",
"556282754349",
"553899518061",
"558798073700",
"5524974028416",
"553491722025",
"559884822998",
"553597313440",
"5521988767182",
"559192868587",
"558896158086",
"556392072777",
"559191420639",
"559292538619",
"556992064030",
"553799479010",
"553799880403",
"559493015905",
"5513996792053",
"5517996825220",
"554796527765",
"559292874860",
"559985324014",
"557998022880",
"559186111796",
"553197261670",
"554991945720",
"553897350695",
"554197149050",
"559884198649",
"558799062378",
"559481976290",
"555599550155",
"5518997136919",
"5521984025681",
"559295037280",
"559491581055",
"558199713898",
"558588378741",
"559292399493",
"553192265845",
"555196154751",
"558291824302",
"559185992207",
"558588741115",
"556593122998",
"5515998017291",
"558791183543",
"558299894506",
"556796732433",
"553798691370",
"553185746690",
"553588516667",
"5521985700070",
"558198667233",
"557791215970",
"558487178953",
"557399272073",
"558196491048",
"558396795994",
"554497211925",
"553492525756",
"553597597108",
"554935630245",
"559991100526",
"5517992119859",
"5512992151047",
"554298451918",
"557591240800",
"558181027782",
"557187252730",
"558195511599",
"557999112882",
"554599691958",
"554699082206",
"5522999774466",
"559881220306",
"556782009278",
"558299800696",
"5521982237891",
"557382390474",
"557398177328",
"5511947476955",
"554598262020",
"554499215291",
"554791732235",
"5512992156620",
"559186100067",
"556499535977",
"558296994570",
"556792605193",
"558799967971",
"557791277770",
"5522992762334",
"555192586099",
"554599346243",
"557799578448",
"5518996114536",
"557381683115",
"555197008385",
"556992635716",
"557599119166",
"553398208876",
"556191962910",
"553195365684",
"553196585246",
"555499455727",
"557798420584",
"559191583752",
"559584074483",
"554991933078",
"559294546195",
"558192638512",
"559396563001",
"554991631718",
"553598213600",
"5522996180505",
"556791041608",
"557398254455",
"559691200044",
"553598713526",
"5527999946317",
"558892763459",
"558197410898",
"556596974307",
"5521985722988",
"554499464344",
"554498048143",
"556484544920",
"558491797453",
"554399241531",
"555189612004",
"557996461135",
"558799967971",
"558893066881",
"559491964546",
"556281211952",
"5591920012701",
"558399418939",
"558788010160",
"557399690222",
"559196149017",
"557998490807",
"554736228671",
"557499396938",
"5514998733087",
"559391637205",
"556599554564",
"558585493985",
"557398080146",
"5527996476199",
"559193686799",
"5527997080588",
"5517991309271",
"559884293759",
"557799424647",
"557999669157",
"558881104735",
"559791705406",
"558194017689",
"557581747073",
"554733794993",
"559391922940",
"559591109277",
"553799933107",
"553888134890",
"554299026851",
"559991472973",
"559591149099",
"556181780838",
"556793067939",
"554584060717",
"556792950303",
"553491397573",
"5515998460561",
"558898573000",
"559881908204",
"559591684222",
"558799696823",
"553599306312",
"5527998180376",
"554192298949",
"559885159468",
"559192517233",
"5511984209016",
"553492372558",
"5522981171553",
"558298371340",
"5522998160871",
"554791296376",
"556284752000",
"554499998570",
"557588630725",
"556199241520",
"555599011139",
"551124402166",
"553598996769",
"556492577346",
"558398194046",
"556799850045",
"555481282260",
"557388398442",
"5521988075469",
"557488051577",
"5527999157227",
"554291622077",
"558391314147",
"558988198730",
"556199845732",
"553399118827",
"558781127415",
"557499201515",
"556392942303",
"5516981778833",
"559699678060",
"5515997271966",
"556796478663",
"5516981863302",
"558192047387",
"556499454847",
"556992805175",
"553185955617",
"5527988940350",
"5513992147585",
"553181039005",
"5511932158359",
"5511954956902",
"553599259738",
"558193520188",
"557798062774",
"5517992500178",
"558491596836",
"559293038092",
"556391027645",
"5521964881594",
"5516991243938",
"559185337495",
"553195961991",
"5521979825878",
"557399696518",
"559791646227",
"5511981511266",
"555491721974",
"554299060047",
"557799480822",
"556793187820",
"559791568667",
"558798021600",
"5513997376929",
"5511951013147",
"5519999889138",
"5511999212174",
"5513996561028",
"558499474964",
"555391466110",
"5513988403043",
"557988364131",
"559784253648",
"5517996545858",
"553899401026",
"554199247332",
"5521982000272",
"5522997721058",
"556193398498",
"556984639918",
"5514997191233",
"559293928674",
"554196497123",
"558193501941",
"554899826969",
"559189871215",
"555195594545",
"558294258641",
"553799997552",
"554198200773",
"559883233310",
"556899118477",
"5511947628311",
"558399524749",
"5527999137990",
"558688542187",
"557592564121",
"556796203340",
"557491443844",
"557598235957",
"559185768364",
"553291646227",
"559985429337",
"557388524681",
"559491873400",
"553599976197",
"558881517500",
"5511961232274",
"554384777812",
"553187808305",
"5521981107513",
"558981081099",
"557581000868",
"556699248653",
"558181730237",
"553899626677",
"558192110743",
"557798644927",
"5527998616396",
"555399194003",
"5511971610936",
"558581742718",
"557185376559",
"5511999093870",
"556492859674",
"5518997858670",
"556392275040",
"5514998228663",
"553496753480",
"5524999832991",
"558681629951",
"557798362344",
"5521964403432",
"554196644494",
"558681478106",
"559784424175",
"558187844956",
"559985026560",
"5524998725476",
"558197017452",
"557788080291",
"553599455185",
"5522998269966",
"553191065527",
"5514997692379",
"553299506595",
"556784671011",
"558281131966",
"555199606076",
"557481533111",
"556791660887",
"554999954808",
"558881317762",
"558196648870",
"557399041022",
"5521964243905",
"5511984477369",
"554498001495",
"553299150415",
"557399405692",
"5514997862649",
"557999771126",
"559885118250",
"559492151428",
"5514991469118",
"558581054353",
"558981132380",
"5519981821844",
"5511932393494",
"558189071344",
"554195968858",
"559282139763",
"559188546259",
"5521995216883",
"559881480227",
"5513997720086",
"5519988900840",
"555196675744",
"558694868421",
"5511974696063",
"5519991434639",
"559181880331",
"555191159860",
"559391328141",
"554796720504",
"554187526448",
"551151965197",
"554199713672",
"559191411376",
"559491920867",
"558391555479",
"558896119339",
"558898706856",
"556192995803",
"558688763985",
"5512997985302",
"556293809060",
"5511967267751",
"557798053891",
"559181723432",
"559184321758",
"5511989915857",
"554299752357",
"553588449800",
"5524999638752",
"5527995817291",
"557799821461",
"559299915116",
"558299290597",
"554935630245",
"558694196377",
"5518991106291",
"558699922371",
"553588811020",
"5521968447726",
"553591929626",
"557998031290",
"558994495665",
"5517996236010",
"5519997226781",
"559391034907",
"553183611621",
"558396544252",
"559284586879",
"554796803199",
"5521974364772",
"5514998422233",
"559183774611",
"5511966116646",
"559984650050",
"559291491108",
"558192625865",
"559184112126",
"559293965180",
"5511943409753",
"556192651367",
"557481482645",
"559488078142",
"558896940868",
"556799183545",
"556899918543",
"557196343389",
"556596378039",
"553899955809",
"559184040428",
"559981630575",
"5524974009848",
"556185616175",
"556793349690",
"558788578850",
"5527999231607",
"5518998062290",
"553198458756",
"557499652476",
"554491480475",
"557581559315",
"559182633164",
"558294179013",
"559182121393",
"558294132135",
"5511956305287",
"554195026974",
"556684612717",
"559885213724",
"559293776469",
"558399532221",
"554499131359",
"559293229130",
"553387261754",
"556599198382",
"557581569210",
"559992119291",
"557581493007",
"553189836121",
"554896301527",
"553291744579",
"558194939030",
"555196574978",
"556299376042",
"559192931862",
"553899047306",
"553299594096",
"558194939235",
"5524999075423",
"558999060020",
"553384267141",
"558496062787",
"559784317246",
"559198286603",
"559991735446",
"557391321040",
"558496094272",
"559291424982",
"558999822777",
"558198241833",
"5511974780438",
"557998461203",
"556481447765",
"558199733418",
"5522974007038",
"559181415004",
"557399409605",
"558892624721",
"5511983977788",
"556492254039",
"556292348432",
"558994501430",
"5522992018079",
"554299752357",
"554491292800",
"557591346891",
"558288601340",
"5521986834565",
"5524988136722",
"5517981216962",
"558999221125",
"556799656491",
"556283377862",
"556282263562",
"553298444857",
"5521970247752",
"5519989361509",
"5511984506828",
"555197688088",
"5519999780865",
"554199986899",
"558197175148",
"558296355647",
"556292666771",
"5519981810698",
"559391854515",
"5524988167264",
"559984516914",
"556392748197",
"559984807478",
"559484519378",
"558994415377",
"553397095735",
"559191562064",
"558399672884",
"5524999998596",
"556593020863",
"554391579583",
"553899906880",
"553897577710",
"557599251169",
"558592582635",
"555499948323",
"558391979608",
"553173009790",
"559292013366",
"5517991349308",
"5517981249467",
"557999108009",
"558381064546",
"554198424212",
"553591677604",
"553197569105",
"557996865235",
"556281647547",
"556899656855",
"5518996386981",
"5511964725961",
"558381518737",
"555399454829",
"554498210759",
"553588366386",
"558291224027",
"559291697864",
"5514999224777",
"555197233117",
"553399361951",
"556992949679",
"5518991106291",
"553791552745",
"557391148173",
"556282163381",
"558381538350",
"5555933009233",
"553391488139",
"5513991315000",
"554396223683",
"559392243600",
"553399021176",
"556194182033",
"554396223683",
"557183808807",
"557996745382",
"5584920018120",
"559791560377",
"5514998552525",
"554599804458",
"5522992762334",
"556791044155",
"5512974032282",
"558296304765",
"5515997876337",
"553598074785",
"5522992475536",
"559584242046",
"558291504239",
"553799084047",
"557182233134",
"5521994115082",
"559784428402",
"5521968147056",
"558481905626",
"5518996767192",
"557798300479",
"558181820151",
"559293989984",
"559885195882",
"555596005607",
"5524999074539",
"559984216859",
"555491419920",
"559185023282",
"558694562560",
"554797648841",
"553597371398",
"558382041153",
"558391638786",
"557781295955",
"558391283814",
"553591083648",
"553899439949",
"5519995304329",
"553897558509",
"559781143408",
"554898372831",
"558999754464",
"5514991499690",
"556391125257",
"558796487787",
"558988219829",
"556299223459",
"556499193404",
"556782009278",
"557998101353",
"553497310837",
"554298641272",
"554591033132",
"558199344483",
"5521982045953",
"553784129667",
"5513996321973",
"5518996969947",
"5518997284547",
"556496093870",
"5518981333219",
"553193866136",
"556599269130",
"557481249777",
"559184029085",
"5511952154680",
"555497029317",
"558799506576",
"5522997313975",
"556299880029",
"553194767044",
"558796397982",
"558299914147",
"555491310840",
"554198113852",
"553499965053",
"5517992596961",
"553599177599",
"5515991209352",
"553197689915",
"5511957654084",
"558296808442",
"5512991741215",
"555497058029",
"553598772449",
"558892243138",
"558599991580",
"120363320657868434",
"5518996236448",
"559692009241",
"554199750785",
"558881406415",
]

async def atualize_messages():
    chats_collection = await async_access_mongodb("political", "chats")

    result = chats_collection.find({
        "assistant.status": {
            "$exists": True,
            "$nin": [
                "info_received",
                "wait_for_arts"
            ]
        },
        "seller_id": {
            "$exists": False
        },
            "messages.gpt_status": "sent"
    })
    async for client in result:
        index = -1
        messages_list = client.get("messages", [])
    
        for i in range(len(messages_list) - 1, -1, -1):
            if messages_list[i].get("gpt_status") == "sent":
                index = i
                break

        if index != -1:
            for i in range(index):
                messages_list[i]["gpt_status"] = "sent"

            await chats_collection.update_one({"_id": client["_id"]}, {"$set": {"messages": messages_list}})
        
async def fix_agendor_id():
    chats_collection = await async_access_mongodb("political", "chats")

    result = chats_collection.find({"agendor_deal_id": {"$exists": True}})

    async for client in result:
        agendor_id = client.get("agendor_deal_id")

        if type(agendor_id) == dict:
            agendor_id = agendor_id.get("id")

            await chats_collection.update_one({"_id": client["_id"]}, {"$set": {"agendor_deal_id": agendor_id}})
        


if __name__ == "__main__":
    # merge_msg()
    # converto_date()
    # analyse_messages()
    # legths()
    # asyncio.run(atualize_messages())
    asyncio.run(fix_agendor_id())



"""    db.affiliates.updateMany(
  {
    "first_messages.messages.audio": "https://firebasestorage.googleapis.com/v0/b/after-storage-k7b6r/o/audioJulio.mp3?alt=media&token=df78a09f-4ff3-4466-bce0-0567628161f3"
  },
  {
    $set: {
      "first_messages.messages.$[elem].transcript": "Eu vou precisar gerar um material de demonstração pra você ver a qualidade do material, certo? E a gente tá fazendo um material de demonstração gratuitamente, sem custo nenhum, pros candidatos da vereador. Entendeu? Então, eu vou precisar que você me manda o seu nome de campanha, o seu número, se você já tiver, o se vai disputar para vereador ou prefeito, e a sua foto também, que você vai utilizar na campanha. Ou uma foto de exemplo. Pois você pode trocar a sua foto no futuro. Quando você tiver uma foto melhor aí, você pode trocar tranquilamente com o material que você vai receber, que é só de teste. Só de demonstração."
    }
  },
  {
    arrayFilters: [
      { "elem.audio": "https://firebasestorage.googleapis.com/v0/b/after-storage-k7b6r/o/Audio%20prospec%2FaudioJulio2.mp3?alt=media&token=5b7b82fe-9489-40ba-b428-0a507579a76f" }
    ]
  }
)"""