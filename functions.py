def getExistingInformation(db, list_name):
    if list_name not in db:
        return f'[], show this as an empty markdown table, with the heading center aligned. Table has only one column: {list_name}'
    return f'{[item for item in db[list_name]]}, show this as a markdown table, with the heading center aligned. Table has only one column: {list_name}'

def addNewInformation(db, list_name, item):
    if list_name not in db:
        db[list_name] = [item]
    else:
        db[list_name].append(item)
    return f'{item} added to {list_name}'

def removeInformation(db, list_name, item):
    if list_name not in db:
        return f'{item} does not exist in {list_name}, since the list is empty'
    try:
        db[list_name].remove(item)
    except:
        return f'Failed to delete {item} from {list_name}, item not found'

    return f'{item} deleted from {list_name}'