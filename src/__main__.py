import json

#-----------------------------------------------------------
#   MAIN
#-----------------------------------------------------------

def main(args):
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--debug", "-d", dest="debug", action="store_true", default=False, help="Verbose output")
    parser.add_argument("--file", required=True, type=str)
    parser.add_argument("--threejs", type=str, help="Export as threejs object")
    options = parser.parse_args()

    if options.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    import w3d
    model = w3d.W3DModel.from_file(options.file)

    if 0:
        import yaml
        yaml.add_representer(Vector, lambda dumper, vector: dumper.represent_scalar('Vector', '%s, %s, %s' % (vector.x, vector.y, vector.z)))
        yaml.add_representer(Quaternion, lambda dumper, q: dumper.represent_scalar('Quaternion', '%s, %s, %s, %s' % (q.w, q.x, q.y, q.z)))
        print(yaml.dump(model))
        exit(0)

    if options.threejs:
        data = model.as_threejs()
        with open(options.threejs, "w") as fw:
            fw.write(json.dumps(data, indent=2))
            print(json.dumps(data, indent=2))

    else:
        print(json.dumps(model.as_threejs(), indent=2))



if __name__ == "__main__":
    import os
    import libs.nicelogging as logging
    logging.config(
        levels={
            "requests": logging.WARN,
        },
        format='%(c)s%(levelicon)s %(runtime)5.1fs [%(name)16s:%(lineno)4s]: %(message)s%(nc)s'
    )

    import sys
    main(sys.argv[1:])
