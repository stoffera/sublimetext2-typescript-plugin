// Parts of this file: Copyright (c) Microsoft. All rights reserved.

///<reference path='./tssrc/compiler/typescript.ts'/>

module TypeScript {

	export class ScriptInfo {
        public version: number;
        public editRanges: { length: number; editRange: TypeScript.ScriptEditRange; }[] = [];

        constructor (public name: string, public content: string, public isResident: bool, public maxScriptVersions: number) {
            this.version = 1;
        }

        public updateContent(content: string, isResident: bool) {
            this.editRanges = [];
            this.content = content;
            this.isResident = isResident;
            this.version++;
        }

        public editContent(minChar: number, limChar: number, newText: string) {
            // Apply edits
            var prefix = this.content.substring(0, minChar);
            var middle = newText;
            var suffix = this.content.substring(limChar);
            this.content = prefix + middle + suffix;

            // Store edit range + new length of script
            this.editRanges.push({ 
                length: this.content.length, 
                editRange: new TypeScript.ScriptEditRange(minChar, limChar, (limChar - minChar) + newText.length)
            });

            if (this.editRanges.length > this.maxScriptVersions) {
                this.editRanges.splice(0, this.maxScriptVersions - this.editRanges.length);
            }

            // Update version #
            this.version++;
        }

        public getEditRangeSinceVersion(version: number): TypeScript.ScriptEditRange {
            if (this.version == version) {
                // No edits!
                return null;
            }

            var initialEditRangeIndex = this.editRanges.length - (this.version - version);
            if (initialEditRangeIndex < 0 || initialEditRangeIndex >= this.editRanges.length) {
                // Too far away from what we know
                return TypeScript.ScriptEditRange.unknown();
            }

            var entries = this.editRanges.slice(initialEditRangeIndex);

            var minDistFromStart = entries.map(x => x.editRange.minChar).reduce((prev, current) => Math.min(prev, current));
            var minDistFromEnd = entries.map(x => x.length - x.editRange.limChar).reduce((prev, current) => Math.min(prev, current));
            var aggDelta = entries.map(x => x.editRange.delta).reduce((prev, current) => prev + current);

            return new TypeScript.ScriptEditRange(minDistFromStart, entries[0].length - minDistFromEnd, aggDelta);
        }
    }
}